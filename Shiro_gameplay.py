import pygame
import sys
import time
import chess
from Shiro_management import ChessBoardManager
from Shiro_NNxMTCS import ChessAIEngine


class GameplayLogic:
    def __init__(self):
        self.board_manager = ChessBoardManager()
        self.ai_engine = None
        self.game_mode = None
        self.game_history = []
        self.analysis_results = {}

    def initialize_ai(self, num_simulations=200):
        """Khởi tạo AI engine"""
        self.ai_engine = ChessAIEngine(num_simulations=num_simulations)
        print(f"AI Engine initialized with {num_simulations} simulations")

    def analyze_position(self, board_state=None):
        """Phân tích thế cờ hiện tại"""
        if board_state is None:
            board_state = self.board_manager.board

        if not self.ai_engine:
            self.initialize_ai()

        analysis = {
            'best_move': None,
            'top_moves': [],
            'position_evaluation': 0,
            'recommendation': ''
        }

        try:
            # Lấy nước đi tốt nhất
            best_move, action_probs = self.ai_engine.get_best_move(board_state)
            analysis['best_move'] = best_move

            # Đánh giá thế cờ
            board_tensor = self.ai_engine.mcts._state_to_tensor(board_state)
            _, value = self.ai_engine.nn.predict(board_tensor)
            analysis['position_evaluation'] = value

            # Lấy top moves
            legal_moves = list(board_state.legal_moves)
            move_probs = []

            for move in legal_moves:
                move_idx = self.move_to_simple_index(move)
                if move_idx < len(action_probs):
                    prob = action_probs[move_idx]
                    move_probs.append((move, prob))

            move_probs.sort(key=lambda x: x[1], reverse=True)
            analysis['top_moves'] = move_probs[:5]  # Top 5 moves

            # Đưa ra khuyến nghị
            if value > 0.5:
                analysis['recommendation'] = "WHITE has significant advantage"
            elif value > 0.1:
                analysis['recommendation'] = "WHITE has slight advantage"
            elif value < -0.5:
                analysis['recommendation'] = "BLACK has significant advantage"
            elif value < -0.1:
                analysis['recommendation'] = "BLACK has slight advantage"
            else:
                analysis['recommendation'] = "Position is roughly equal"

        except Exception as e:
            analysis['recommendation'] = f"Analysis error: {str(e)}"

        self.analysis_results = analysis
        return analysis

    def get_analysis_display(self):
        """Chuẩn bị text để hiển thị phân tích"""
        if not self.analysis_results:
            return "No analysis available"

        analysis = self.analysis_results
        lines = []

        lines.append("=== POSITION ANALYSIS ===")
        lines.append(f"Evaluation: {analysis['position_evaluation']:.3f}")
        lines.append(f"Recommendation: {analysis['recommendation']}")

        if analysis['best_move']:
            lines.append(f"Best move: {analysis['best_move'].uci()}")

        lines.append("Top moves:")
        for i, (move, score) in enumerate(analysis['top_moves']):
            lines.append(f"  {i + 1}. {move.uci()} ({score:.4f})")

        return "\n".join(lines)

    # ... (giữ nguyên các phương thức khác)

    def move_to_simple_index(self, move):
        """Chuyển move sang index đơn giản"""
        return (move.from_square * 64 + move.to_square) % 4672

    def run_ai_vs_ai_game(self, max_moves=100):
        """
        Chạy một ván đấu AI vs AI và in ra log, lịch sử nước đi, và bàn cờ.
        """
        if not self.ai_engine:
            self.initialize_ai()

        self.board_manager.reset_board()  # Đảm bảo board mới

        print("=== BẮT ĐẦU VÁN AI VS AI ===")
        print(f"Trạng thái ban đầu (FEN): {self.board_manager.get_fen()}")
        print("\nBàn cờ hiện tại:\n" + self.board_manager.get_board_visual())

        move_count = 0
        while not self.board_manager.board.is_game_over() and move_count < max_moves:

            current_board = self.board_manager.board

            # 1. Xác định lượt và AI
            color_turn = "Trắng" if current_board.turn == chess.WHITE else "Đen"

            print(f"\n--- Lượt {move_count // 2 + 1} ({color_turn} đang suy nghĩ...) ---")

            # 2. AI tìm nước đi tốt nhất
            best_move, _ = self.ai_engine.get_best_move(current_board)

            if best_move is None:
                print(f"LỖI: {color_turn} không tìm thấy nước đi hợp lệ. Kết thúc ván.")
                break

            move_uci = best_move.uci()

            # 3. Thực hiện nước đi
            # Lưu ý: make_move nên nằm trong ChessBoardManager và tự động cập nhật move_history
            success = self.board_manager.make_move(move_uci)

            if success:
                # 4. Thông báo qua log
                print(f"LOG NƯỚC ĐI: {color_turn} đi {move_uci}")

                # 5. In thông tin bàn cờ (text tree)
                print(f"FEN hiện tại: {self.board_manager.get_fen()}")
                print("\nBàn cờ hiện tại:\n" + self.board_manager.get_board_visual())

                move_count += 1
            else:
                print(f"LỖI: Không thể thực hiện nước đi {move_uci}. Kết thúc ván.")
                break

        # 6. Kết quả ván đấu và Lịch sử
        result = self.board_manager.get_game_result()
        print("\n=== VÁN ĐẤU KẾT THÚC ===")
        print(f"Kết quả cuối cùng: {result}")
        print(f"Tổng số nước đi: {move_count}")
        print("\n=== LỊCH SỬ NƯỚC ĐI (PGN) ===")
        print(self.board_manager.get_pgn())

        return result

    def ai_vs_ai_next_move(self):
        """
        Chạy nước đi tiếp theo cho AI hiện tại.
        Trả về True nếu nước đi thành công, False nếu game kết thúc/lỗi.
        """
        board_state = self.board_manager.board

        if board_state.is_game_over():
            # Game đã kết thúc
            return False, "Game Over"

        if not self.ai_engine:
            self.initialize_ai()

        try:
            # AI tìm nước đi tốt nhất
            best_move, _ = self.ai_engine.get_best_move(board_state)

            if best_move is None:
                return False, "AI cannot find a move"

            move_uci = best_move.uci()

            # Thực hiện nước đi
            success = self.board_manager.make_move(move_uci)

            if success:
                # Trả về move_uci thành công để log
                return True, move_uci
            else:
                return False, "Invalid move attempted"

        except Exception as e:
            # print(f"Lỗi trong quá trình AI di chuyển: {e}")
            return False, f"Error: {e}"