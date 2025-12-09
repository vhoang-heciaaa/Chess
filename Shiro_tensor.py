import chess
import numpy as np

def Chess_tensor(pgn_text):
    class ChessBoardManager:
        def __init__(self):
            self.board = chess.Board()

        def is_valid_move(self, move):
            """Kiểm tra nước đi hợp lệ"""
            try:
                return move in self.board.legal_moves
            except:
                return False

        def update_board(self, move):
            """Cập nhật bàn cờ sau mỗi nước đi"""
            if self.is_valid_move(move):
                self.board.push(move)
                return True
            return False

        def is_game_over(self):
            """Kiểm tra kết thúc ván cờ"""
            return self.board.is_game_over()

        def get_game_result(self):
            """Xác định kết quả ván cờ"""
            if self.board.is_checkmate():
                return "White wins" if self.board.turn == chess.BLACK else "Black wins"
            elif self.board.is_stalemate():
                return "Draw by stalemate"
            elif self.board.is_insufficient_material():
                return "Draw by insufficient material"
            elif self.board.is_fifty_moves():
                return "Draw by fifty-move rule"
            elif self.board.is_repetition():
                return "Draw by repetition"
            return "Game in progress"

        def encode_board_to_tensor(self):
            """Mã hóa bàn cờ thành dictionary chứa các tensor riêng biệt"""

            # Khởi tạo các tensor riêng biệt
            tensor_dict = {}

            # 1. Tensor quân cờ theo màu và loại (6 kênh × 2 màu = 12 kênh)
            piece_tensors = {}
            piece_types = ['PAWN', 'KNIGHT', 'BISHOP', 'ROOK', 'QUEEN', 'KING']

            for color in [chess.WHITE, chess.BLACK]:
                color_name = 'WHITE' if color == chess.WHITE else 'BLACK'
                for piece_type in piece_types:
                    tensor_name = f"{color_name}_{piece_type}"
                    tensor = np.zeros((8, 8), dtype=np.float32)
                    piece_mask = self.board.pieces(getattr(chess, piece_type), color)

                    for square in piece_mask:
                        row, col = divmod(square, 8)
                        tensor[7 - row, col] = 1  # Lật hàng để đúng góc nhìn

                    piece_tensors[tensor_name] = tensor
                    tensor_dict[tensor_name] = tensor

            # 2. Tensor lượt đi
            turn_tensor = np.ones((8, 8), dtype=np.float32) if self.board.turn else np.zeros((8, 8), dtype=np.float32)
            tensor_dict['TURN'] = turn_tensor

            # 3. Tensor nhập thành (4 kênh riêng biệt)
            castle_tensors = {
                'WHITE_KINGSIDE': np.ones((8, 8), dtype=np.float32) if self.board.has_kingside_castling_rights(
                    chess.WHITE) else np.zeros((8, 8), dtype=np.float32),
                'WHITE_QUEENSIDE': np.ones((8, 8), dtype=np.float32) if self.board.has_queenside_castling_rights(
                    chess.WHITE) else np.zeros((8, 8), dtype=np.float32),
                'BLACK_KINGSIDE': np.ones((8, 8), dtype=np.float32) if self.board.has_kingside_castling_rights(
                    chess.BLACK) else np.zeros((8, 8), dtype=np.float32),
                'BLACK_QUEENSIDE': np.ones((8, 8), dtype=np.float32) if self.board.has_queenside_castling_rights(
                    chess.BLACK) else np.zeros((8, 8), dtype=np.float32)
            }
            tensor_dict.update(castle_tensors)

            # 4. Tensor En Passant
            ep_tensor = np.zeros((8, 8), dtype=np.float32)
            if self.board.ep_square is not None:
                row, col = divmod(self.board.ep_square, 8)
                ep_tensor[7 - row, col] = 1
            tensor_dict['EN_PASSANT'] = ep_tensor

            # 5. Tensor số nước đi (cho luật 50 nước)
            halfmove_tensor = np.full((8, 8), self.board.halfmove_clock / 50.0, dtype=np.float32)
            tensor_dict['HALFMOVE_CLOCK'] = halfmove_tensor

            # 6. Tensor tổng số nước đi
            fullmove_tensor = np.full((8, 8), self.board.fullmove_number / 100.0, dtype=np.float32)
            tensor_dict['FULLMOVE_NUMBER'] = fullmove_tensor

            return tensor_dict

        def get_combined_tensor(self):
            """Kết hợp tất cả tensor thành 1 tensor lớn (8x8xN) cho Neural Network"""
            tensor_dict = self.encode_board_to_tensor()

            # Tính tổng số kênh
            num_channels = len(tensor_dict)
            combined = np.zeros((8, 8, num_channels), dtype=np.float32)

            # Ghép các tensor theo channel
            for i, (name, tensor) in enumerate(tensor_dict.items()):
                combined[:, :, i] = tensor

            return combined, list(tensor_dict.keys())

        def get_legal_moves_tensor(self):
            """Tạo tensor nước đi hợp lệ dạng 8x8x8x8"""
            legal_moves = np.zeros((8, 8, 8, 8), dtype=np.float32)

            for move in self.board.legal_moves:
                from_row, from_col = divmod(move.from_square, 8)
                to_row, to_col = divmod(move.to_square, 8)

                # Chuyển đổi tọa độ (lật hàng)
                legal_moves[7 - from_row, from_col, 7 - to_row, to_col] = 1

            return legal_moves

        def get_compact_legal_moves(self):
            """Tạo tensor nước đi hợp lệ dạng 64x64 (đầu vào NN)"""
            legal_moves = np.zeros((64, 64), dtype=np.float32)

            for move in self.board.legal_moves:
                legal_moves[move.from_square, move.to_square] = 1

            return legal_moves

        def print_tensor_info(self):
            """In thông tin chi tiết về các tensor"""
            tensor_dict = self.encode_board_to_tensor()

            print("=== CHESS BOARD TENSORS ===")
            print(f"Total tensors: {len(tensor_dict)}")
            print("\nIndividual tensors (8x8):")

            for name, tensor in tensor_dict.items():
                print(f"\n{name}:")
                print(f"  Shape: {tensor.shape}")
                print(f"  Sum: {np.sum(tensor)}")
                print(f"  Range: [{np.min(tensor):.1f}, {np.max(tensor):.1f}]")

    # Ví dụ sử dụng chi tiết
    if __name__ == "__main__":
        board_manager = ChessBoardManager()

        # Thực hiện vài nước đi để test
        moves = ["e2e4", "e7e5", "g1f3", "b8c6"]
        for move_uci in moves:
            move = chess.Move.from_uci(move_uci)
            if board_manager.is_valid_move(move):
                board_manager.update_board(move)
                print(f"Executed: {move_uci}")

        # Lấy tensor dictionary
        tensor_dict = board_manager.encode_board_to_tensor()

        # In thông tin tensor
        board_manager.print_tensor_info()

        # Lấy tensor kết hợp
        combined_tensor, channel_names = board_manager.get_combined_tensor()
        print(f"\nCombined tensor shape: {combined_tensor.shape}")
        print(f"Channel names: {channel_names}")

        # Lấy tensor nước đi hợp lệ
        legal_moves_4d = board_manager.get_legal_moves_tensor()
        legal_moves_2d = board_manager.get_compact_legal_moves()
        print(f"Legal moves 4D shape: {legal_moves_4d.shape}")
        print(f"Legal moves 2D shape: {legal_moves_2d.shape}")
        print(f"Total legal moves: {np.sum(legal_moves_2d)}")

        # Kiểm tra trạng thái game
        print(f"\nGame over: {board_manager.is_game_over()}")
        print(f"Current result: {board_manager.get_game_result()}")
        print(f"Current turn: {'WHITE' if board_manager.board.turn else 'BLACK'}")