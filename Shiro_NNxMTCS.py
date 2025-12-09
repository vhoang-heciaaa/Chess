import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import math
import random
import time
import os
from collections import defaultdict
import chess
from Shiro_management import ChessBoardManager


from performance_boost import GPUInferenceEngine, CPUMoveValidator

# Đặt các hằng số này ngoài hàm (hoặc trong class) để dễ quản lý
BASE_PROMOTION_INDEX = 4096
# Thứ tự quân phong cấp không phải Hậu: Mã, Tượng, Xe (N, B, R)
PROMOTION_PIECES = [chess.KNIGHT, chess.BISHOP, chess.ROOK]
# Giả sử 576 slots / 3 loại quân = 192 slots cho mỗi loại (Dựa trên cấu trúc NN 4672)
SLOTS_PER_PROMOTION = 192


class EnhancedChessNeuralNetwork:
    def __init__(self, input_shape=(8, 8, 20), policy_output_shape=4672):
        self.input_shape = input_shape
        self.policy_output_shape = policy_output_shape
        self.model = self._build_enhanced_model()

    def _build_enhanced_model(self):
        """Xây dựng Neural Network cải tiến với residual connections"""
        inputs = tf.keras.Input(shape=self.input_shape)

        # Initial convolution
        x = layers.Conv2D(256, 3, padding='same')(inputs)
        x = layers.BatchNormalization()(x)
        x = layers.Activation('relu')(x)

        # Residual blocks (3 blocks thay vì 10 để đỡ nặng)
        for i in range(3):
            residual = x
            x = layers.Conv2D(256, 3, padding='same')(x)
            x = layers.BatchNormalization()(x)
            x = layers.Activation('relu')(x)
            x = layers.Conv2D(256, 3, padding='same')(x)
            x = layers.BatchNormalization()(x)

            # Skip connection
            if residual.shape[-1] != x.shape[-1]:
                residual = layers.Conv2D(256, 1, padding='same')(residual)
                residual = layers.BatchNormalization()(residual)

            x = layers.add([x, residual])
            x = layers.Activation('relu')(x)

        # Policy head
        policy_conv = layers.Conv2D(128, 3, padding='same', activation='relu')(x)
        policy_conv = layers.BatchNormalization()(policy_conv)
        policy_flat = layers.Flatten()(policy_conv)
        policy_dense = layers.Dense(512, activation='relu')(policy_flat)
        policy_dense = layers.Dropout(0.3)(policy_dense)
        policy_output = layers.Dense(self.policy_output_shape, activation='softmax', name='policy')(policy_dense)

        # Value head
        value_conv = layers.Conv2D(64, 3, padding='same', activation='relu')(x)
        value_conv = layers.BatchNormalization()(value_conv)
        value_flat = layers.Flatten()(value_conv)
        value_dense = layers.Dense(256, activation='relu')(value_flat)
        value_dense = layers.Dropout(0.3)(value_dense)
        value_dense = layers.Dense(64, activation='relu')(value_dense)
        value_output = layers.Dense(1, activation='tanh', name='value')(value_dense)

        model = tf.keras.Model(inputs=inputs, outputs=[policy_output, value_output])

        # Optimizer với learning rate schedule
        optimizer = tf.keras.optimizers.Adam(learning_rate=0.001, clipnorm=1.0)

        model.compile(
            optimizer=optimizer,
            loss={
                'policy': 'categorical_crossentropy',
                'value': 'mse'
            },
            loss_weights={'policy': 1.0, 'value': 1.0},
            metrics={
                'policy': 'accuracy',
                'value': 'mae'
            }
        )

        return model

    def predict(self, board_tensor):
        """Dự đoán policy và value từ tensor bàn cờ"""
        if len(board_tensor.shape) == 3:
            board_tensor = np.expand_dims(board_tensor, axis=0)

        policy, value = self.model.predict(board_tensor, verbose=0)
        return policy[0], value[0][0]

    def train(self, training_data, epochs=10, batch_size=32, progress_callback=None):
        """Huấn luyện network trên dữ liệu training với callback tiến trình"""
        if not training_data:
            print("No training data available")
            return None

        states, policy_targets, value_targets = zip(*training_data)

        states = np.array(states)
        policy_targets = np.array(policy_targets)
        value_targets = np.array(value_targets)

        # Custom callback để theo dõi tiến trình
        class ProgressCallback(tf.keras.callbacks.Callback):
            def on_epoch_begin(self, epoch, logs=None):
                if progress_callback:
                    progress = (epoch / epochs) * 100
                    progress_callback(progress, f"Bắt đầu epoch {epoch + 1}/{epochs}")

            def on_epoch_end(self, epoch, logs=None):
                if progress_callback:
                    progress = ((epoch + 1) / epochs) * 100
                    status = f"Epoch {epoch + 1}/{epochs} - policy_loss: {logs['policy_loss']:.4f}, value_loss: {logs['value_loss']:.4f}"
                    progress_callback(progress, status)

        print(f"Training on {len(training_data)} samples for {epochs} epochs...")

        history = self.model.fit(
            states,
            {
                'policy': policy_targets,
                'value': value_targets
            },
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.1,
            verbose=0,
            callbacks=[ProgressCallback()]
        )

        return history

    def save_model(self, filepath):
        """Lưu model"""
        self.model.save(filepath)
        print(f"Model saved to {filepath}")

    def load_model(self, filepath):
        """Tải model"""
        if os.path.exists(filepath):
            self.model = tf.keras.models.load_model(filepath)
            print(f"Model loaded from {filepath}")
        else:
            print(f"Model file {filepath} not found, using new model")


class EnhancedMCTSNode:
    def __init__(self, state, parent=None, move=None, prior=0):
        self.state = state  # Board state
        self.parent = parent
        self.move = move  # Move that led to this node
        self.prior = prior  # Prior probability from NN

        self.children = []
        self.visit_count = 0
        self.value_sum = 0
        self.is_expanded = False
        self.virtual_loss = 0  # For parallel MCTS

    @property
    def value(self):
        """Giá trị trung bình của node (đã bù virtual loss)"""
        if self.visit_count == 0:
            return 0
        return (self.value_sum - self.virtual_loss) / self.visit_count

    def is_leaf(self):
        """Kiểm tra node lá"""
        return not self.is_expanded

    def progressive_widening(self, policy_probs, max_children=25):
        """Chỉ mở rộng các nước đi có xác suất cao nhất (ĐÃ SỬA LỖI)"""
        legal_moves = list(self.state.legal_moves)

        if not legal_moves:
            self.is_expanded = True
            return

        # Kết hợp xác suất và legal moves
        move_probs = []
        for move in legal_moves:
            # [LƯU Ý QUAN TRỌNG] Hàm _move_to_index ở đây phải đồng bộ với hàm bên ChessAIEngine
            # Nếu chưa sửa _move_to_index trong class này, hãy sửa ngay!
            move_idx = self._move_to_index(move)

            if move_idx < len(policy_probs):
                # [FIX QUAN TRỌNG] Ép kiểu numpy value về float chuẩn của Python
                # Điều này ngăn lỗi "The truth value of an array..." khi sort
                prob = float(policy_probs[move_idx])
                move_probs.append((move, prob))
            else:
                move_probs.append((move, 0.001))  # Small probability for unmapped moves

        # Sắp xếp theo xác suất giảm dần
        # Bây giờ x[1] là float chuẩn nên sort sẽ hoạt động trơn tru
        move_probs.sort(key=lambda x: x[1], reverse=True)

        # Chỉ mở rộng top moves
        for move, prob in move_probs[:max_children]:
            new_state = self.state.copy()
            new_state.push(move)
            child = EnhancedMCTSNode(new_state, parent=self, move=move, prior=prob)
            self.children.append(child)

        self.is_expanded = True
        # Chỉ mở rộng top moves
        for move, prob in move_probs[:max_children]:
            new_state = self.state.copy()
            new_state.push(move)
            child = EnhancedMCTSNode(new_state, parent=self, move=move, prior=prob)
            self.children.append(child)

        self.is_expanded = True

    def select_child(self, exploration_weight=1.4):
        """Chọn child node theo UCB1 cải tiến"""
        best_score = -float('inf')
        best_child = None

        total_visits = sum(child.visit_count for child in self.children)

        for child in self.children:
            if child.visit_count == 0:
                # Ưu tiên các node chưa được thăm
                ucb_score = float('inf')
            else:
                # UCB1 formula với prior và virtual loss compensation
                exploitation = child.value
                exploration = exploration_weight * child.prior * math.sqrt(total_visits) / (1 + child.visit_count)
                ucb_score = exploitation + exploration

            if ucb_score > best_score:
                best_score = ucb_score
                best_child = child

        return best_child

    def add_virtual_loss(self):
        """Thêm virtual loss để đa dạng hóa tìm kiếm"""
        self.virtual_loss += 1
        self.visit_count += 1  # Tạm thời tăng visit count

    def revert_virtual_loss(self):
        """Hoàn tác virtual loss"""
        self.virtual_loss -= 1
        self.visit_count -= 1

    def _move_to_index(self, move):
        """Chuyển đổi move sang index (ĐỒNG BỘ VỚI ChessAIEngine)"""
        # [FIX] Sử dụng logic mới, bỏ modulo % 4672

        # Hằng số (nên import hoặc define lại nếu cần)
        BASE_PROMOTION_INDEX = 4096
        PROMOTION_PIECES = [chess.KNIGHT, chess.BISHOP, chess.ROOK]
        SLOTS_PER_PROMOTION = 192

        # 1. Non-Promotion và Queen Promotion
        if not move.promotion or move.promotion == chess.QUEEN:
            return move.from_square * 64 + move.to_square

        # 2. Non-Queen Promotion
        try:
            piece_type_offset = PROMOTION_PIECES.index(move.promotion)
        except ValueError:
            return 0  # Fallback an toàn

        move_offset = (move.from_square // 64) * 64 + (move.to_square % 64)
        return BASE_PROMOTION_INDEX + (piece_type_offset * SLOTS_PER_PROMOTION) + move_offset


class EnhancedMonteCarloTreeSearch:
    def __init__(self, neural_network, num_simulations=800, exploration_weight=1.4, max_children=25):
        self.nn = neural_network
        self.num_simulations = num_simulations
        self.exploration_weight = exploration_weight
        self.max_children = max_children

    def search(self, board_state, progress_callback=None):
        """Thực hiện MCTS cải tiến từ trạng thái bàn cờ hiện tại"""
        root = EnhancedMCTSNode(board_state)

        for sim in range(self.num_simulations):
            if progress_callback and sim % 100 == 0:
                progress = (sim / self.num_simulations) * 100
                progress_callback(progress, f"MCTS simulation {sim}/{self.num_simulations}")

            node = root
            search_path = [node]

            # Selection: đi xuống leaf node
            while not node.is_leaf():
                node.add_virtual_loss()  # Áp dụng virtual loss
                node = node.select_child(self.exploration_weight)
                search_path.append(node)

            # Expansion và Evaluation
            if not node.state.is_game_over():
                # Lấy dự đoán từ Neural Network trực tiếp
                board_tensor = self._state_to_tensor(node.state)
                policy_probs, value = self.nn.predict(board_tensor)
                node.progressive_widening(policy_probs, self.max_children)
            else:
                # Game over, tính giá trị kết quả
                value = self._get_game_result_value(node.state)

            # Backpropagation với virtual loss compensation
            self._enhanced_backpropagate(search_path, value)

        return self._get_action_probabilities(root)

    def _enhanced_backpropagate(self, search_path, value):
        """Backpropagation cải tiến với virtual loss compensation"""
        for node in reversed(search_path):
            node.visit_count += 1
            # Bù virtual loss: giá trị thực = value - virtual_loss
            actual_value = value - node.virtual_loss
            node.value_sum += actual_value
            node.revert_virtual_loss()  # Hoàn tác virtual loss
            value = -value  # Đảo giá trị cho perspective của đối thủ

    def _state_to_tensor(self, board_state):
        """Chuyển board state sang tensor input cho NN"""
        tensor = np.zeros((8, 8, 20), dtype=np.float32)

        # Piece placement (12 channels)
        piece_types = [chess.PAWN, chess.KNIGHT, chess.BISHOP,
                       chess.ROOK, chess.QUEEN, chess.KING]

        for square in chess.SQUARES:
            piece = board_state.piece_at(square)
            if piece:
                row, col = divmod(square, 8)
                channel = (piece.piece_type - 1) + (6 if piece.color else 0)
                tensor[7 - row, col, channel] = 1

        # Additional information (8 channels)
        # Turn (1 channel)
        tensor[:, :, 12] = 1.0 if board_state.turn == chess.WHITE else 0.0

        # Castling rights (4 channels)
        tensor[:, :, 13] = 1.0 if board_state.has_kingside_castling_rights(chess.WHITE) else 0.0
        tensor[:, :, 14] = 1.0 if board_state.has_queenside_castling_rights(chess.WHITE) else 0.0
        tensor[:, :, 15] = 1.0 if board_state.has_kingside_castling_rights(chess.BLACK) else 0.0
        tensor[:, :, 16] = 1.0 if board_state.has_queenside_castling_rights(chess.BLACK) else 0.0

        # En passant (1 channel)
        if board_state.ep_square is not None:
            row, col = divmod(board_state.ep_square, 8)
            tensor[7 - row, col, 17] = 1.0

        # Move counts (2 channels)
        tensor[:, :, 18] = board_state.halfmove_clock / 50.0
        tensor[:, :, 19] = board_state.fullmove_number / 100.0

        return tensor

    def _get_game_result_value(self, board_state):
        """Chuyển kết quả game sang giá trị [-1, 1]"""
        if board_state.is_checkmate():
            return -1.0 if board_state.turn == chess.WHITE else 1.0
        elif board_state.is_stalemate():
            return 0.0
        elif board_state.is_insufficient_material():
            return 0.0
        elif board_state.can_claim_draw():
            return 0.0
        elif board_state.is_fifty_moves():
            return 0.0
        elif board_state.is_repetition():
            return 0.0
        return 0.0  # Game vẫn tiếp tục

    def _get_action_probabilities(self, root):
        """Lấy xác suất hành động dựa trên visit count"""
        action_probs = np.zeros(4672)  # Policy output shape

        if not root.children:
            return action_probs

        total_visits = sum(child.visit_count for child in root.children)

        if total_visits == 0:
            # Nếu không có visit nào, phân bố đều
            for child in root.children:
                move_idx = child._move_to_index(child.move)
                action_probs[move_idx] = 1.0 / len(root.children)
        else:
            # Phân bố theo visit count
            for child in root.children:
                move_idx = child._move_to_index(child.move)
                action_probs[move_idx] = child.visit_count / total_visits

        return action_probs

    def _index_to_move(self, index, board_state):

        if index < BASE_PROMOTION_INDEX:
            # Index 0-4095: Non-Promotion và Queen Promotion
            from_square = index // 64
            to_square = index % 64

            # Kiểm tra nếu nước đi này là phong cấp
            if board_state.piece_at(from_square) == chess.Piece(chess.PAWN, board_state.turn):
                # Xác định hàng phong cấp
                if board_state.turn == chess.WHITE:
                    is_promotion_rank = chess.square_rank(to_square) == 7
                else:  # BLACK
                    is_promotion_rank = chess.square_rank(to_square) == 0

                if is_promotion_rank:
                    # Trong block 4096, phong cấp mặc định là Hậu (Queen)
                    return chess.Move(from_square, to_square, promotion=chess.QUEEN)

            # Nước đi bình thường
            return chess.Move(from_square, to_square)

        else:
            # Index 4096-4671: Non-Queen Promotion (N, B, R)

            promotion_index = index - BASE_PROMOTION_INDEX

            # 1. Xác định loại quân phong cấp (N, B, R)
            piece_type_offset = promotion_index // SLOTS_PER_PROMOTION

            if piece_type_offset >= len(PROMOTION_PIECES):
                # Index nằm ngoài phạm vi 4672
                return chess.Move.null()

            promotion_piece = PROMOTION_PIECES[piece_type_offset]

            # 2. Xác định from_square và to_square từ index còn lại
            move_offset = promotion_index % SLOTS_PER_PROMOTION

            # LƯU Ý: Ánh xạ 192 slots này rất đặc thù và PHỤ THUỘC vào _move_to_index.
            # Cấu trúc dưới đây là GIẢ ĐỊNH.

            # Giả định ánh xạ 64x3: (from_square * 64 + to_square)
            from_square = (move_offset // 64) * 64
            to_square = move_offset % 64

            # Cần phải sửa phần này nếu logic của bạn khác. Tốt nhất là sử dụng một hàm
            # ánh xạ 192 slots (ví dụ: 8 file x 8 square x 3 type) chính xác.

            # Tạm thời trả về nước đi null để không làm crash, nhưng phần này cần được FIX.
            # return chess.Move(from_square, to_square, promotion=promotion_piece) # <--- Chỉ dùng nếu chắc chắn
            return chess.Move.null()


class ChessAIEngine:
    def __init__(self, model_path=None, num_simulations=800, use_opening_book=True):
        self.board_manager = ChessBoardManager()
        self.nn = EnhancedChessNeuralNetwork()

        # Khởi tạo MCTS trực tiếp với neural network
        self.mcts = EnhancedMonteCarloTreeSearch(
            neural_network=self.nn,
            num_simulations=num_simulations,
            exploration_weight=1.4,
            max_children=25)

        self.use_opening_book = use_opening_book
        self.opening_book = self._load_opening_book()
        self.training_data = []
        self.performance_stats = {
            'games_played': 0,
            'wins': 0,
            'losses': 0,
            'draws': 0
        }
        if model_path:
            self.nn.load_model(model_path)

    def _load_opening_book(self):
        """Tải opening book đơn giản"""
        opening_book = {
            # Starting position
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1": [
                "e2e4", "d2d4", "c2c4", "g1f3"
            ],
            # After 1.e4
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1": [
                "e7e5", "c7c5", "e7e6", "c7c6", "g8f6"
            ],
            # After 1.d4
            "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1": [
                "d7d5", "g8f6", "f7f5", "c7c5"
            ]
        }
        return opening_book

    def get_best_move(self, board_state=None, temperature=0.1, progress_callback=None):
        """Tính nước đi tốt nhất với các cải tiến (ĐÃ SỬA LỖI)"""
        if board_state is None:
            board_state = self.board_manager.board

        # 1. Kiểm tra opening book
        if self.use_opening_book and len(board_state.move_stack) < 6:
            opening_moves = self.opening_book.get(board_state.fen())
            if opening_moves:
                for move_uci in opening_moves:
                    move = chess.Move.from_uci(move_uci)
                    if move in board_state.legal_moves:
                        if progress_callback:
                            progress_callback(100, f"Sử dụng opening book: {move_uci}")
                        return move, None

        # 2. Kiểm tra endgame tactic
        if self.is_endgame(board_state):
            endgame_move = self.get_endgame_move(board_state)
            if endgame_move:
                if progress_callback:
                    progress_callback(100, f"Sử dụng endgame tactic: {endgame_move.uci()}")
                return endgame_move, None

        # 3. Sử dụng MCTS enhanced để tìm xác suất
        action_probs = self.mcts.search(board_state, progress_callback)

        # 4. Chọn nước đi dựa trên temperature
        legal_moves = list(board_state.legal_moves)
        best_move = None

        if not legal_moves:
            return None, action_probs

        if temperature > 0:
            # Áp dụng temperature
            action_probs = self._apply_temperature(action_probs, temperature)

            # Tạo distribution chỉ cho legal moves
            legal_probs = []
            for move in legal_moves:
                move_idx = self._move_to_index(move)
                if move_idx < len(action_probs):
                    legal_probs.append(action_probs[move_idx])
                else:
                    legal_probs.append(0.001)  # Small probability

            # [FIX 1] Normalize an toàn hơn (tránh NaN và sum=0)
            legal_probs = np.array(legal_probs)
            prob_sum = np.sum(legal_probs)

            if prob_sum > 0 and not np.isnan(prob_sum):
                legal_probs = legal_probs / prob_sum
                # Chọn ngẫu nhiên theo trọng số xác suất
                move_idx = np.random.choice(len(legal_moves), p=legal_probs)
                best_move = legal_moves[move_idx]
            else:
                # Fallback nếu xác suất bị lỗi
                best_move = random.choice(legal_moves)
        else:
            # Chọn move có xác suất cao nhất (Deterministic)
            best_prob = -1

            for move in legal_moves:
                move_idx = self._move_to_index(move)
                if move_idx < len(action_probs):
                    prob = action_probs[move_idx]
                    if prob > best_prob:
                        best_prob = prob
                        best_move = move

            if best_move is None:
                best_move = random.choice(legal_moves)

        # [FIX 2] Lớp bảo vệ cuối cùng: Đảm bảo best_move KHÔNG PHẢI là mảng NumPy
        if isinstance(best_move, np.ndarray):
            print(f"CẢNH BÁO LỖI: best_move là numpy array ({best_move.shape})! Đang chuyển đổi...")

            legal_moves = list(board_state.legal_moves)

            try:
                # 1. Tìm index có xác suất/score cao nhất
                best_move_index = np.argmax(best_move)

                # 2. Chuyển index thành chess.Move (Dùng hàm trong MCTS)
                # YÊU CẦU: Hàm _index_to_move phải được định nghĩa trong self.mcts
                best_move = self.mcts._index_to_move(best_move_index, board_state)

                # Kiểm tra lại tính hợp lệ sau khi chuyển đổi
                if best_move not in legal_moves:
                    print(f"Move đã giải mã ({best_move.uci()}) không hợp lệ. Dùng Fallback.")
                    best_move = random.choice(legal_moves) if legal_moves else None

            except Exception as e:
                # 3. Fallback an toàn nếu conversion lỗi
                print(f"Lỗi khi chuyển đổi NumPy array sang chess.Move: {e}. Dùng Fallback.")
                best_move = random.choice(legal_moves) if legal_moves else None

        return best_move, action_probs

    def _apply_temperature(self, probs, temperature):
        """Áp dụng temperature cho probability distribution"""
        if temperature <= 0:
            return probs

        # Tránh log(0)
        probs = np.clip(probs, 1e-8, 1.0)
        probs = probs ** (1 / temperature)
        return probs / np.sum(probs)

    def _move_to_index(self, move):

        # 1. Non-Promotion và Queen Promotion (Index 0-4095)
        if not move.promotion or move.promotion == chess.QUEEN:
            # LOẠI BỎ % 4672 để tránh collision!
            return move.from_square * 64 + move.to_square

        # 2. Non-Queen Promotion (N, B, R) (Index 4096-4671)

        # Xác định offset dựa trên loại quân (N=0, B=1, R=2)
        try:
            piece_type_offset = PROMOTION_PIECES.index(move.promotion)
        except ValueError:
            # Nếu không phải N, B, R, hoặc Q (đã xử lý ở trên)
            return -1  # Hoặc raise lỗi

        # Tính toán chỉ số: BASE_INDEX + (Offset quân) * 192 + (Offset di chuyển)
        # LƯU Ý: Đây là phần cần phải khớp với logic _index_to_move
        # Đây là logic GIẢ ĐỊNH:
        move_offset = (move.from_square // 64) * 64 + (move.to_square % 64)

        return BASE_PROMOTION_INDEX + (piece_type_offset * SLOTS_PER_PROMOTION) + move_offset

    def is_endgame(self, board_state):
        """Kiểm tra có phải endgame không"""
        pieces = board_state.piece_map()
        if len(pieces) <= 8:  # Rất ít quân
            # Đếm major pieces (hậu, xe)
            major_pieces = 0
            queens = 0
            for piece in pieces.values():
                if piece.piece_type == chess.QUEEN:
                    queens += 1
                if piece.piece_type in [chess.QUEEN, chess.ROOK]:
                    major_pieces += 1
            return queens == 0 or major_pieces <= 1
        return False

    def get_endgame_move(self, board_state):
        """Chiến thuật đơn giản cho endgame"""
        legal_moves = list(board_state.legal_moves)

        # Ưu tiên chiếu hết nếu có thể
        for move in legal_moves:
            board_copy = board_state.copy()
            board_copy.push(move)
            if board_copy.is_checkmate():
                return move

        # Ưu tiên promotion
        for move in legal_moves:
            if move.promotion and move.promotion == chess.QUEEN:
                return move

        # Ưu tiên chiếu
        for move in legal_moves:
            board_copy = board_state.copy()
            board_copy.push(move)
            if board_copy.is_check():
                return move

        return None

    def self_play(self, num_games=100, save_interval=10, progress_callback=None):
        """Tự chơi để tạo dữ liệu training với callback tiến trình"""
        print(f"Starting self-play for {num_games} games...")

        for game_idx in range(num_games):
            if progress_callback:
                progress = (game_idx / num_games) * 50  # 50% cho self-play
                progress_callback(progress, f"Self-play game {game_idx + 1}/{num_games}")

            self.board_manager.reset_board()
            game_history = []
            moves_count = 0

            while not self.board_manager.is_game_over() and moves_count < 200:  # Giới hạn 200 nước
                # Lấy nước đi từ AI với temperature cao để exploration
                best_move, action_probs = self.get_best_move(temperature=1.0)

                # Lưu training data
                board_tensor = self.mcts._state_to_tensor(self.board_manager.board)
                game_history.append((board_tensor, action_probs))

                # Thực hiện nước đi
                if best_move:
                    self.board_manager.make_move(best_move)
                    moves_count += 1
                else:
                    break

            # Tính giá trị kết quả và lưu training data
            result_value = self.mcts._get_game_result_value(self.board_manager.board)

            for board_tensor, action_probs in game_history:
                self.training_data.append((board_tensor, action_probs, result_value))
                result_value = -result_value  # Đảo giá trị cho perspective

            # Cập nhật thống kê
            self._update_performance_stats(result_value)

            # Lưu model định kỳ
            if (game_idx + 1) % save_interval == 0:
                model_path = f"chess_ai_model_selfplay_{game_idx + 1}.h5"
                self.nn.save_model(model_path)

        if progress_callback:
            progress_callback(50, "Self-play completed!")

    def train_on_self_play_data(self, epochs=10, batch_size=32, progress_callback=None):
        """Huấn luyện trên dữ liệu self-play với callback tiến trình"""
        if not self.training_data:
            print("No training data available. Run self_play first.")
            return None

        print(f"Training on {len(self.training_data)} samples for {epochs} epochs...")

        def training_progress(progress, status):
            if progress_callback:
                # Chuyển từ 50-100% cho training phase
                adjusted_progress = 50 + (progress / 100) * 50
                progress_callback(adjusted_progress, status)

        history = self.nn.train(
            self.training_data,
            epochs=epochs,
            batch_size=batch_size,
            progress_callback=training_progress
        )

        # Lưu model sau training
        self.nn.save_model("chess_ai_model_trained.h5")

        return history

    def _update_performance_stats(self, result_value):
        """Cập nhật thống kê hiệu suất"""
        self.performance_stats['games_played'] += 1

        if result_value > 0.5:
            self.performance_stats['wins'] += 1
        elif result_value < -0.5:
            self.performance_stats['losses'] += 1
        else:
            self.performance_stats['draws'] += 1

    def get_performance_stats(self):
        """Lấy thống kê hiệu suất"""
        stats = self.performance_stats.copy()
        total_games = stats['games_played']
        if total_games > 0:
            stats['win_rate'] = (stats['wins'] / total_games) * 100
        else:
            stats['win_rate'] = 0.0
        return stats

    def set_difficulty(self, num_simulations=None, exploration_weight=None, max_children=None):
        """Điều chỉnh độ khó AI"""
        if num_simulations:
            self.mcts.num_simulations = num_simulations

        if exploration_weight:
            self.mcts.exploration_weight = exploration_weight

        if max_children:
            self.mcts.max_children = max_children

        print(f"AI Difficulty updated: Simulations={self.mcts.num_simulations}, "
              f"Exploration={self.mcts.exploration_weight}, MaxChildren={self.mcts.max_children}")

    def analyze_position(self, board_state=None):
        """Phân tích thế cờ hiện tại"""
        if board_state is None:
            board_state = self.board_manager.board

        analysis = {
            'best_move': None,
            'top_moves': [],
            'position_evaluation': 0,
            'win_probability': 0.5,
            'recommendation': ''
        }

        try:
            # Lấy nước đi tốt nhất
            best_move, action_probs = self.get_best_move(board_state, temperature=0.0)
            analysis['best_move'] = best_move

            # Đánh giá thế cờ
            board_tensor = self.mcts._state_to_tensor(board_state)
            _, value = self.nn.predict(board_tensor)
            analysis['position_evaluation'] = value
            analysis['win_probability'] = (value + 1) / 2  # Chuyển từ [-1,1] sang [0,1]

            # Lấy top moves
            legal_moves = list(board_state.legal_moves)
            move_probs = []

            for move in legal_moves:
                move_idx = self._move_to_index(move)
                if move_idx < len(action_probs):
                    prob = action_probs[move_idx]
                    move_probs.append((move, prob))

            move_probs.sort(key=lambda x: x[1], reverse=True)
            analysis['top_moves'] = move_probs[:5]  # Top 5 moves

            # Đưa ra khuyến nghị
            if value > 0.5:
                analysis['recommendation'] = "TRẮNG có lợi thế lớn"
            elif value > 0.1:
                analysis['recommendation'] = "TRẮNG có lợi thế nhỏ"
            elif value < -0.5:
                analysis['recommendation'] = "ĐEN có lợi thế lớn"
            elif value < -0.1:
                analysis['recommendation'] = "ĐEN có lợi thế nhỏ"
            else:
                analysis['recommendation'] = "Thế cờ cân bằng"

        except Exception as e:
            analysis['recommendation'] = f"Lỗi phân tích: {str(e)}"

        return analysis

    def update_ai_series_results(self):
        """Cập nhật kết quả series AI vs AI"""
        if self.board_manager.board.is_game_over():
            if self.board_manager.board.is_checkmate():
                if self.board_manager.board.turn == chess.BLACK:  # Trắng thắng
                    self.ai_vs_ai_results['white_wins'] += 1
                else:  # Đen thắng
                    self.ai_vs_ai_results['black_wins'] += 1
            else:  # Hòa
                self.ai_vs_ai_results['draws'] += 1


# Ví dụ sử dụng và test
if __name__ == "__main__":
    # Khởi tạo AI Engine
    ai_engine = ChessAIEngine(num_simulations=100)

    print("=== ENHANCED CHESS AI ENGINE ===")
    print("Testing basic functionality...")

    # Test chế độ dễ
    ai_engine.set_difficulty(num_simulations=50, exploration_weight=2.0, max_children=15)

    # Tạo bàn cờ test
    test_board = ChessBoardManager()

    print("Initial board:")
    print(test_board.get_board_visual())

    # AI chọn nước đi
    print("\nAI calculating best move...")
    best_move, action_probs = ai_engine.get_best_move(test_board.board)

    if best_move:
        print(f"AI recommends: {best_move.uci()}")

        # Thực hiện nước đi
        test_board.make_move(best_move)
        print("\nBoard after AI move:")
        print(test_board.get_board_visual())
    else:
        print("AI could not find a valid move!")

    # Test phân tích
    print("\n=== POSITION ANALYSIS ===")
    analysis = ai_engine.analyze_position(test_board.board)
    print(f"Evaluation: {analysis['position_evaluation']:.3f}")
    print(f"Win Probability: {analysis['win_probability']:.1%}")
    print(f"Recommendation: {analysis['recommendation']}")
    if analysis['best_move']:
        print(f"Best Move: {analysis['best_move'].uci()}")

    print("\nTop moves:")
    for i, (move, score) in enumerate(analysis['top_moves']):
        print(f"  {i + 1}. {move.uci()} (score: {score:.4f})")

    # Self-play demo (số game ít để test)
    print("\n=== SELF-PLAY DEMO (2 games) ===")
    ai_engine.self_play(num_games=2, save_interval=1)

    # Training demo
    print("\n=== TRAINING DEMO ===")
    if ai_engine.training_data:
        history = ai_engine.train_on_self_play_data(epochs=2)
        print("Training completed!")

        # Test AI sau training
        print("\nTesting AI after training...")
        test_board2 = ChessBoardManager()
        best_move2, _ = ai_engine.get_best_move(test_board2.board)
        print(f"AI move after training: {best_move2.uci() if best_move2 else 'None'}")

    # Hiển thị thống kê
    stats = ai_engine.get_performance_stats()
    print(f"\nPerformance Stats: {stats['wins']}W - {stats['losses']}L - {stats['draws']}D")
    print(f"Win Rate: {stats['win_rate']:.1f}%")