# performance_boost.py
import threading
import numpy as np
import tensorflow as tf
from collections import deque
import time
import os
import chess


class GPUInferenceEngine:
    """Engine chuyên xử lý inference trên GPU"""

    def __init__(self, model, memory_limit_mb=2048):
        """
        Chỉ dùng GPU cho inference
        """
        self.model = model
        self.memory_limit_mb = memory_limit_mb
        self._setup_gpu()

        # Batch processing queue
        self.queue = deque()
        self.results = {}
        self.lock = threading.Lock()
        self.cond = threading.Condition()
        self.running = True

        # Worker thread
        self.worker = threading.Thread(target=self._inference_worker, daemon=True)
        self.worker.start()

        print(f"GPU Inference Engine ready (Memory: {memory_limit_mb}MB)")

    def _setup_gpu(self):
        """Cấu hình GPU chỉ cho inference"""
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            try:
                # Enable memory growth để tránh chiếm toàn bộ VRAM
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)

                # Giới hạn memory cho inference
                tf.config.set_logical_device_configuration(
                    gpus[0],
                    [tf.config.LogicalDeviceConfiguration(memory_limit=self.memory_limit_mb)]
                )
            except RuntimeError as e:
                print(f"GPU config error: {e}")
        else:
            print("No GPU found, using CPU for inference")

    def predict_batch(self, state_tensors):
        """
        Dự đoán batch nhiều state cùng lúc
        Trả về: (policy_array, value_array)
        """
        if not state_tensors:
            return [], []

        # Tạo batch tensor
        if len(state_tensors[0].shape) == 3:
            batch_array = np.stack(state_tensors)
        else:
            batch_array = np.array(state_tensors)

        try:
            # Inference trên GPU
            policy_batch, value_batch = self.model.predict(
                batch_array,
                verbose=0,
                batch_size=min(len(state_tensors), 8)  # Batch size vừa phải
            )

            # Trả về kết quả
            policies = [policy_batch[i] for i in range(len(state_tensors))]
            values = [value_batch[i][0] for i in range(len(state_tensors))]

            return policies, values

        except Exception as e:
            print(f"GPU inference error: {e}")
            # Fallback: random policies
            policies = [np.random.random(4672) for _ in state_tensors]
            values = [0.0 for _ in state_tensors]
            return policies, values

    def predict_single(self, state_tensor):
        """Dự đoán single state (wrapper cho batch)"""
        policies, values = self.predict_batch([state_tensor])
        return policies[0], values[0]

    def async_predict(self, state_tensor, callback):
        """Async prediction với callback"""
        # Thêm vào queue
        request_id = str(time.time())
        request = {
            'id': request_id,
            'tensor': state_tensor,
            'callback': callback,
            'timestamp': time.time()
        }

        with self.lock:
            self.queue.append(request)
            self.results[request_id] = {'done': False, 'result': None}

        # Thông báo worker
        with self.cond:
            self.cond.notify()

    def _inference_worker(self):
        """Worker xử lý async inference"""
        while self.running:
            requests = []

            # Thu thập batch requests
            with self.lock:
                while self.queue and len(requests) < 8:  # Batch size 8
                    requests.append(self.queue.popleft())

            if requests:
                # Chuẩn bị batch
                tensors = [req['tensor'] for req in requests]

                try:
                    # Batch inference
                    policies, values = self.predict_batch(tensors)

                    # Gọi callbacks
                    for i, req in enumerate(requests):
                        result = (policies[i], values[i])
                        if req['callback']:
                            req['callback'](result)

                        # Lưu kết quả
                        self.results[req['id']]['result'] = result
                        self.results[req['id']]['done'] = True

                except Exception as e:
                    print(f"Async inference error: {e}")

            else:
                # Chờ requests mới
                with self.cond:
                    self.cond.wait(timeout=0.1)

    def stop(self):
        """Dừng inference engine"""
        self.running = False
        with self.cond:
            self.cond.notify()
        self.worker.join(timeout=1.0)


class CPUMoveValidator:
    """Engine CPU chuyên xử lý logic và kiểm tra nước đi"""

    @staticmethod
    def get_legal_moves(board_state):
        """Lấy tất cả nước đi hợp lệ"""
        return list(board_state.legal_moves)

    @staticmethod
    def filter_promising_moves(board_state, policy_probs, top_k=20):
        """
        Lọc top-k nước đi hứa hẹn nhất từ policy
        Trả về: list of (move, prior_probability)
        """
        legal_moves = CPUMoveValidator.get_legal_moves(board_state)

        if not legal_moves:
            return []

        # Tính score cho từng move
        move_scores = []
        for move in legal_moves:
            move_idx = CPUMoveValidator.move_to_index(move)
            if move_idx < len(policy_probs):
                score = policy_probs[move_idx]
            else:
                score = 0.001  # Mặc định thấp
            move_scores.append((move, score))

        # Sắp xếp và chọn top-k
        move_scores.sort(key=lambda x: x[1], reverse=True)
        return move_scores[:top_k]

    @staticmethod
    def move_to_index(move):
        """Chuyển move thành index trong policy vector"""
        # Đơn giản: from_square * 64 + to_square
        return (move.from_square * 64 + move.to_square) % 4672

    @staticmethod
    def simulate_move(board_state, move):
        """Mô phỏng nước đi, trả về board mới"""
        new_board = board_state.copy()
        new_board.push(move)
        return new_board

    @staticmethod
    def evaluate_position_simple(board_state):
        """Đánh giá vị trí đơn giản bằng CPU (material count)"""
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0
        }

        score = 0
        for square in chess.SQUARES:
            piece = board_state.piece_at(square)
            if piece:
                value = piece_values.get(piece.piece_type, 0)
                if piece.color == chess.WHITE:
                    score += value
                else:
                    score -= value

        return score / 39.0  # Normalize về [-1, 1]