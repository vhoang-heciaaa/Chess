# Shiro_UIUX.py - SHIRO CHESS ENGINE UI/UX (PHIÊN BẢN HOÀN CHỈNH - FIX HIỂN THỊ TRAINING & LOG)
import pygame
import sys
import chess
import os
import time
import threading
import random
from pygame.locals import *

# ======================================================================
# 1. IMPORTS & FALLBACKS
# ======================================================================
# Định nghĩa một sự kiện người dùng tùy chỉnh để signal UI cần cập nhật
USEREVENT_UPDATE_UI = pygame.USEREVENT + 1

try:
    # Cần đảm bảo các file này nằm cùng cấp thư mục hoặc trong PYTHONPATH
    from Shiro_management import ChessBoardManager
    from Shiro_NNxMTCS import ChessAIEngine
    from Shiro_gameplay import GameplayLogic
    # Giả định draw_chess_board nằm trong thư mục con chess_simple_data
    from chess_simple_data.chess_board_draw import draw_chess_board
except ImportError as e:
    print(f"LỖI FATAL: Không tìm thấy module cần thiết: {e}")
    print(
        "Vui lòng kiểm tra các file: Shiro_management.py, Shiro_NNxMTCS.py, Shiro_gameplay.py, và chess_simple_data/chess_board_draw.py")


    # Tạo các class fallback đơn giản để UI có thể khởi động
    class ChessBoardManager:
        def __init__(self, fen=None):
            self.board = chess.Board()

        def make_move(self, move):
            try:
                self.board.push(move)
                return True
            except:
                return False

        def reset_board(self):
            self.board = chess.Board()
            if hasattr(self, 'move_history'):
                self.move_history.clear()
            return True

        def undo_move(self):
            try:
                self.board.pop()
                return True
            except IndexError:
                return False

        def is_valid_move(self, move):
            return move in self.board.legal_moves

        def set_fen(self, fen):
            self.board = chess.Board(fen)  # Thêm set_fen


    class ChessAIEngine:
        def __init__(self, num_simulations=200):
            pass

        def get_best_move(self, board, is_self_play=False):
            legal = list(board.legal_moves)
            return (random.choice(legal), 0) if legal else (None, 0)

        # Cập nhật fallback self_play để khớp với signature mới
        def self_play(self, num_games=10, save_interval=5, move_callback=None):
            print("Fallback: self-play skipped. Simulating 5 seconds.")
            for i in range(1, num_games + 1):
                if move_callback:
                    # Giả lập nước đi
                    time.sleep(0.5)
                    move_callback(i, num_games, f"Game {i} - Mock move {i * 2}", chess.STARTING_FEN)
            time.sleep(5)

        def train_on_self_play_data(self, epochs=5):
            print("Fallback: training skipped.")

        def analyze_position(self, board_state, top_k=5):
            return {'best_move': None, 'top_moves': [], 'position_evaluation': 0,
                    'recommendation': 'Fallback AI: No analysis available'}


    class GameplayLogic:
        def __init__(self):
            self.board_manager = ChessBoardManager()
            self.ai_engine = ChessAIEngine()
            self.analysis_results = {}

        def analyze_position(self, board_state=None): self.analysis_results = {'position_evaluation': 0,
                                                                               'recommendation': 'No analysis'}

        def get_analysis_display(self): return "Không có phân tích (AI Engine không hoạt động)"


    draw_chess_board = None  # Fallback cho hàm vẽ

# ======================================================================
# 2. HẰNG SỐ UI (Modern Dark Theme)
# ======================================================================
BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8
FPS = 60
SIDEBAR_WIDTH = 320
WINDOW_WIDTH = BOARD_SIZE + SIDEBAR_WIDTH
WINDOW_HEIGHT = 720

BG_COLOR = (30, 30, 40)
PANEL_COLOR = (45, 45, 55)
TEXT_COLOR = (200, 200, 220)
ACCENT_COLOR = (60, 140, 180)
BUTTON_COLOR = (60, 60, 75)
HOVER_COLOR = (80, 80, 100)
WIN_COLOR = (50, 150, 50)

HIGHLIGHT = (247, 247, 105, 150)  # Vàng nhạt (ô đang chọn)
VALID_MOVE = (106, 190, 48, 150)  # Xanh lá cây (nước đi hợp lệ)
LAST_MOVE = (150, 150, 70, 100)  # Xám vàng (nước đi cuối cùng)
CHECK_COLOR = (255, 0, 0, 150)  # Đỏ (ô vua bị chiếu)

BUTTON_HEIGHT = 45
BUTTON_MARGIN = 12
PANEL_START_X = BOARD_SIZE + 20


# ======================================================================
# 3. CLASS TRAINING THREAD (UPDATED)
# ======================================================================
class TrainingThread(threading.Thread):
    """Thread để chạy huấn luyện AI mà không làm đơ UI"""

    # CHỈNH SỬA: Thêm move_callback
    def __init__(self, ai_engine, callback, move_callback):
        super().__init__()
        self.ai_engine = ai_engine
        self.callback = callback
        self.move_callback = move_callback  # <-- Callback cho từng nước đi
        self.progress = 0
        self.status = "Đang chuẩn bị..."
        self.is_running = True

    def run(self):
        try:
            # 1. Self-Play (Thu thập dữ liệu)
            self.status = "Đang thu thập dữ liệu self-play (10 ván)..."
            if hasattr(self.ai_engine, 'self_play'):
                # CHỈNH SỬA: Pass move_callback vào self_play
                self.ai_engine.self_play(num_games=10, save_interval=5, move_callback=self.move_callback)
            self.progress = 50

            if not self.is_running: return

            # 2. Training (Huấn luyện NN)
            self.status = "Đang huấn luyện neural network (5 epochs)..."
            if hasattr(self.ai_engine, 'train_on_self_play_data'):
                self.ai_engine.train_on_self_play_data(epochs=5)
            self.progress = 100

            if not self.is_running: return

            self.status = "Huấn luyện hoàn thành!"
            self.callback(True, "Huấn luyện hoàn thành! AI đã học thêm kinh nghiệm mới.")

        except Exception as e:
            self.callback(False, f"Lỗi trong quá trình Training: {str(e)}")

    def stop(self):
        self.is_running = False


# ======================================================================
# 4. CLASS CHESS GUI (UPDATED)
# ======================================================================
class ChessGUI:
    def __init__(self, title="Shiro Chess Engine"):
        pygame.init()
        self.title = title
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(self.title)
        self.clock = pygame.time.Clock()
        self.running = True

        # --- Khởi tạo Font ---
        self.font_name = pygame.font.match_font('segoeui, arial, freesans, Noto Sans CJK JP')
        self.title_font = pygame.font.Font(self.font_name, 28)
        self.font = pygame.font.Font(self.font_name, 20)
        self.small_font = pygame.font.Font(self.font_name, 15)
        self.button_font = pygame.font.Font(self.font_name, 18)

        # --- Khởi tạo Logic và Game Components ---
        try:
            self.game_logic = GameplayLogic()
            self.board_manager = self.game_logic.board_manager
            self.ai_engine = self.game_logic.ai_engine
            self.mcts = getattr(self.ai_engine, "mcts", None) if self.ai_engine else None
        except Exception as e:
            print(f"Không thể khởi tạo Game Logic/AI Engine: {e}")
            self.game_logic = None
            self.board_manager = ChessBoardManager()
            self.ai_engine = None
            self.mcts = None

        # --- AI vs AI state ---
        self.ai_vs_ai_games = 1
        self.ai_vs_ai_current_game = 0
        self.ai_vs_ai_results = {
            'white_wins': 0,
            'black_wins': 0,
            'draws': 0
        }
        self.is_ai_vs_ai_series = False
        self.ai_vs_ai_worker = None

        # --- Popup state for AI vs AI ---
        self.popup_input_text = "1"
        self.input_rect = pygame.Rect(PANEL_START_X, 400, 100, 30)
        self.input_active = False

        # --- UI state / Game state ---
        self.selected_square = None
        self.valid_moves = []
        self.last_move = None
        self.game_mode = "menu"
        self.current_player_mode = "human_vs_ai"
        self.human_color = chess.WHITE
        self.ai_thinking = False
        self.game_history_display = []
        self.active_buttons = []
        self.buttons = {}
        self.difficulty = "MEDIUM"

        # --- Training state (UPDATED) ---
        self.is_training = False
        self.training_progress = 0
        self.training_status = ""
        self.training_thread = None
        self.show_training_results = False
        self.training_result_message = ""
        self.training_game_info = ""  # <-- NEW: Thông tin ván cờ (VD: Game 1/10)

        # --- Performance statistics (cho chế độ human_vs_ai) ---
        self.performance_stats = {
            'games_played': 0,
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'win_rate': 0.0
        }

        # --- Threading / synchronization ---
        self.board_lock = threading.Lock()
        self.turn_is_ai = False
        self.stop_ai_vs_ai = threading.Event()
        #biến cho mode ai vs ai
        self.ai_vs_ai_log_moves = []  # Danh sách lưu log chi tiết từng nước đi
        self.ai_vs_ai_current_log = "Đã sẵn sàng. Chọn 'Bắt đầu Series' để chơi AI vs AI."
        self.ai_vs_ai_thread = None
        self.ai_vs_ai_running = False
        self.ai_vs_ai_game_result = None  # Lưu kết quả cuối cùng
    # --- PHƯƠNG THỨC MỚI: Xử lý Log nước đi từ Training Thread ---
    def _handle_training_move_log(self, current_game, total_games, log_entry, fen):
        """Được gọi bởi TrainingThread để cập nhật UI với nước đi mới (trong Self-Play)."""

        # Cập nhật trạng thái UI
        self.training_game_info = f"Game {current_game}/{total_games}"

        # Cập nhật lịch sử nước đi và trạng thái bàn cờ
        with self.board_lock:
            # Cần reset board bằng FEN để đảm bảo trạng thái chính xác (vì self-play không dùng make_move)
            self.board_manager.set_fen(fen)
            self.game_history_display.append(log_entry)

            # Cập nhật last_move để highlight trên bàn cờ
            try:
                # Trích xuất uci từ log_entry (ví dụ: "1. Trắng: e2e4" -> "e2e4")
                self.last_move = log_entry.split(': ')[-1].split(' ')[0]
            except:
                self.last_move = None

        # Gửi sự kiện để Pygame biết cần redraw (quan trọng cho thread an toàn)
        pygame.event.post(pygame.event.Event(USEREVENT_UPDATE_UI))

        # --- PHƯƠNG THỨC BẮT ĐẦU TRAINING MỚI (Triggered by a button) ---

    def _training_complete_callback(self, success, message):
        """Hàm callback khi quá trình training kết thúc."""
        self.is_training = False
        self.show_training_results = True
        self.training_result_message = message
        self.training_game_info = ""
        print(f"Training kết thúc. Trạng thái: {message}")

    def start_training_series(self):
        if self.is_training:
            print("Đang training, không thể bắt đầu training mới.")
            return

        print("Bắt đầu Huấn Luyện (Self-Play & Training)...")
        self.is_training = True
        self.training_progress = 0
        self.training_status = "Khởi tạo..."
        self.training_game_info = ""
        self.game_history_display = []
        self.board_manager.reset_board()  # Reset board về trạng thái ban đầu

        # Khởi tạo thread mới và pass callback
        self.training_thread = TrainingThread(
            ai_engine=self.ai_engine,
            callback=self._training_complete_callback,
            move_callback=self._handle_training_move_log  # <-- Pass callback
        )
        self.training_thread.start()
        self.game_mode = "ai_vs_ai"  # Chuyển sang mode AI vs AI để dùng panel

    # --- PHƯƠNG THỨC HỖ TRỢ CHUNG ---

    def coords_to_square(self, x, y):
        """Chuyển đổi tọa độ pixel sang ô cờ (chess.SQUARE)."""
        if x < 0 or x >= BOARD_SIZE or y < 0 or y >= BOARD_SIZE:
            return None

        col = x // SQUARE_SIZE
        row = y // SQUARE_SIZE

        # Chuyển đổi từ tọa độ UI (top-left là a8) sang chess.SQUARE (a1 là 0)
        return (7 - row) * 8 + col

    def _update_performance_stats(self, result):
        """Cập nhật thống kê hiệu suất cá nhân."""
        self.performance_stats['games_played'] += 1
        if result is True:
            self.performance_stats['wins'] += 1
        elif result is False:
            self.performance_stats['losses'] += 1
        elif result == 'draw':
            self.performance_stats['draws'] += 1

        total = self.performance_stats['games_played']
        wins = self.performance_stats['wins']
        if total > 0:
            self.performance_stats['win_rate'] = (wins / total) * 100
        else:
            self.performance_stats['win_rate'] = 0.0

    # --- PHƯƠNG THỨC XỬ LÝ CHẾ ĐỘ CHƠI (ĐÃ FIX DELAY VÀ LOG NƯỚC ĐI) ---

    def _ai_vs_ai_series_worker(self):
        """Worker thread chạy chuỗi game AI vs AI, có độ trễ và log để hiển thị."""
        self.stop_ai_vs_ai.clear()
        self.ai_vs_ai_results = {'white_wins': 0, 'black_wins': 0, 'draws': 0}

        MOVE_DELAY = 0.5  # 0.5 giây cho mỗi nước đi (Độ trễ hiển thị)

        print(f"Bắt đầu series AI vs AI: {self.ai_vs_ai_games} ván")

        for i in range(1, self.ai_vs_ai_games + 1):
            if self.stop_ai_vs_ai.is_set():
                break

            self.ai_vs_ai_current_game = i
            self.board_manager.reset_board()
            self.last_move = None
            self.game_history_display = []  # <--- RESET lịch sử cho ván mới

            while not self.board_manager.board.is_game_over() and not self.stop_ai_vs_ai.is_set():
                current_board = self.board_manager.board.copy()

                # 1. Bắt đầu tính toán (Hiển thị "AI Đang Tính Toán..." trên UI)
                self.ai_thinking = True

                # Lấy nước đi
                # Trong chế độ này, ta giả định AI dùng get_best_move thông thường
                move, _ = self.ai_engine.get_best_move(current_board) if self.ai_engine else (None, 0)

                self.ai_thinking = False  # Đặt False ngay sau khi tính toán xong

                if move:
                    move_uci = move.uci()
                    # Tính số thứ tự nước đi (1. e4, 1... e5)
                    move_number = (len(current_board.move_stack) // 2) + 1

                    # LOGGING NƯỚC ĐI (CONSOLE)
                    log_entry = f"{move_number}. {'Trắng' if current_board.turn == chess.WHITE else 'Đen'}: {move_uci}"
                    print(f"[AI vs AI Game {i}] {log_entry}")

                    # 2. Thực hiện nước đi và cập nhật trạng thái UI
                    with self.board_lock:
                        self.board_manager.make_move(move)
                        self.last_move = move_uci
                        self.game_history_display.append(log_entry)  # <--- CẬP NHẬT lịch sử cho UI

                    # Gửi event để force redraw
                    pygame.event.post(pygame.event.Event(USEREVENT_UPDATE_UI))

                    # 3. TẠM DỪNG ĐỂ UI KỊP VẼ NƯỚC ĐI MỚI
                    time.sleep(MOVE_DELAY)
                else:
                    # Nếu AI không tìm được nước đi, kết thúc ván
                    break

                    # Game over, record result
            if not self.stop_ai_vs_ai.is_set():
                result = self.board_manager.board.result()
                if result == "1-0":
                    self.ai_vs_ai_results['white_wins'] += 1
                elif result == "0-1":
                    self.ai_vs_ai_results['black_wins'] += 1
                else:
                    self.ai_vs_ai_results['draws'] += 1

                print(f"Ván {i} kết thúc: {result}. Tỉ số: {self.ai_vs_ai_results}")

            # Dừng lâu hơn giữa các ván
            time.sleep(1.5)

            # Kết thúc series
        self.is_ai_vs_ai_series = False
        self.ai_vs_ai_current_game = 0
        print("AI vs AI Series Finished.")

    def reset_game(self):
        """Khởi động lại ván cờ, dựa trên chế độ đang được chọn."""
        # Dừng series cũ nếu đang chạy
        if self.ai_vs_ai_worker and self.ai_vs_ai_worker.is_alive():
            self.stop_ai_vs_ai.set()
            self.ai_vs_ai_worker.join()

        # Dừng training nếu đang chạy
        if self.training_thread and self.training_thread.is_alive():
            self.training_thread.stop()
            self.training_thread.join()
            self.is_training = False  # <-- Rất quan trọng
            self.training_status = "Đã dừng."

        self.board_manager.reset_board()
        self.selected_square = None
        self.ai_thinking = False
        self.last_move = None
        self.valid_moves = []
        self.game_history_display = []  # <--- Đảm bảo reset lịch sử nước đi

        if self.game_mode == "ai_vs_ai":
            # Chuẩn bị và chạy series mới
            self.is_ai_vs_ai_series = True
            try:
                self.ai_vs_ai_games = int(self.popup_input_text)
                if self.ai_vs_ai_games <= 0:
                    self.ai_vs_ai_games = 1
            except ValueError:
                self.ai_vs_ai_games = 1

            self.ai_vs_ai_current_game = 0
            self.ai_vs_ai_results = {'white_wins': 0, 'black_wins': 0, 'draws': 0}
            self.ai_vs_ai_worker = threading.Thread(target=self._ai_vs_ai_series_worker, daemon=True)
            self.ai_vs_ai_worker.start()
        else:
            self.is_ai_vs_ai_series = False
            self.performance_stats = {
                'games_played': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'win_rate': 0.0
            }

    def switch_game_mode(self):
        """Chuyển đổi chế độ chơi."""
        if self.current_player_mode == "human_vs_ai":
            self.current_player_mode = "ai_vs_ai"
            self.game_mode = "ai_vs_ai"
        else:
            self.current_player_mode = "human_vs_ai"
            self.game_mode = "human_vs_ai"
        self.reset_game()

    def set_difficulty(self, level):
        """Đặt độ khó cho AI."""
        self.difficulty = level
        # Cần thêm logic để cập nhật AI engine (ví dụ: số simulations cho MCTS)
        print(f"Đã đặt độ khó: {level}")

    def trigger_analysis(self):
        """Kích hoạt phân tích thế cờ."""
        if self.game_logic:
            # Chạy phân tích trong một thread để tránh đơ UI
            threading.Thread(target=self.game_logic.analyze_position,
                             args=(self.board_manager.board.copy(),), daemon=True).start()
        print("Đang chạy phân tích...")

    # --- PHƯƠNG THỨC VẼ UI ---

    def draw_button(self, rect, text, is_active=False, color=BUTTON_COLOR, hover_color=HOVER_COLOR):
        """Vẽ một nút bấm với hiệu ứng hover và trạng thái active."""
        mouse_pos = pygame.mouse.get_pos()
        current_color = color

        if is_active:
            current_color = ACCENT_COLOR
        elif rect.collidepoint(mouse_pos):
            current_color = HOVER_COLOR

        pygame.draw.rect(self.screen, current_color, rect, border_radius=8)

        font_to_use = getattr(self, 'button_font', pygame.font.Font(None, 18))
        text_surface = font_to_use.render(text, True, TEXT_COLOR)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

        return rect

    def draw_menu(self):
        """Vẽ menu lựa chọn chế độ chơi."""
        sidebar_rect = pygame.Rect(BOARD_SIZE, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, PANEL_COLOR, sidebar_rect)

        buttons = []
        y_pos = 60

        # Tiêu đề
        title = self.title_font.render("SHIRO CHESS ENGINE", True, ACCENT_COLOR)
        self.screen.blit(title, (PANEL_START_X + 10, y_pos))
        y_pos += 80

        # Nút START GAME
        start_rect = pygame.Rect(PANEL_START_X, y_pos, SIDEBAR_WIDTH - 40, BUTTON_HEIGHT * 1.2)
        buttons.append(('start_game', self.draw_button(start_rect, "BẮT ĐẦU VÁN MỚI", color=WIN_COLOR)))
        y_pos += BUTTON_HEIGHT * 1.2 + BUTTON_MARGIN * 3

        # LỰA CHỌN CHẾ ĐỘ
        mode_label = self.font.render("CHỌN CHẾ ĐỘ:", True, TEXT_COLOR)
        self.screen.blit(mode_label, (PANEL_START_X + 10, y_pos))
        y_pos += 30

        pva_rect = pygame.Rect(PANEL_START_X, y_pos, SIDEBAR_WIDTH - 40, BUTTON_HEIGHT)
        is_pva_active = self.current_player_mode == "human_vs_ai"
        buttons.append(
            ('set_mode_human', self.draw_button(pva_rect, "NGƯỜI vs AI", is_active=is_pva_active, color=BUTTON_COLOR)))
        y_pos += BUTTON_HEIGHT + BUTTON_MARGIN

        ava_rect = pygame.Rect(PANEL_START_X, y_pos, SIDEBAR_WIDTH - 40, BUTTON_HEIGHT)
        is_ava_active = self.current_player_mode == "ai_vs_ai"
        buttons.append(('set_mode_ai',
                        self.draw_button(ava_rect, "AI vs AI (SERIES)", is_active=is_ava_active, color=BUTTON_COLOR)))
        y_pos += BUTTON_HEIGHT + BUTTON_MARGIN * 3

        # Lựa chọn ĐỘ KHÓ
        difficulty_label = self.font.render("CHỌN ĐỘ KHÓ:", True, TEXT_COLOR)
        self.screen.blit(difficulty_label, (PANEL_START_X + 10, y_pos))
        y_pos += 30

        btn_width = (SIDEBAR_WIDTH - 50) // 3
        x_start = PANEL_START_X
        difficulties = [('DỄ', 'EASY'), ('TB', 'MEDIUM'), ('KHÓ', 'HARD')]

        for text, level in difficulties:
            diff_rect = pygame.Rect(x_start, y_pos, btn_width, BUTTON_HEIGHT)
            is_active = self.difficulty == level
            buttons.append((f'set_difficulty_menu_{level}', self.draw_button(diff_rect, text, is_active=is_active)))
            x_start += btn_width + 5

        y_pos += BUTTON_HEIGHT + BUTTON_MARGIN * 3

        # INPUT CHO AI VS AI SERIES (Chỉ hiện khi chế độ AI vs AI được chọn)
        if self.current_player_mode == "ai_vs_ai":
            input_label = self.small_font.render("Số ván AI vs AI (1-100):", True, TEXT_COLOR)
            self.screen.blit(input_label, (PANEL_START_X + 10, y_pos))

            # Vẽ input box
            self.input_rect = pygame.Rect(PANEL_START_X, y_pos + 20, SIDEBAR_WIDTH - 40, 30)
            color = HOVER_COLOR if self.input_active else BUTTON_COLOR
            pygame.draw.rect(self.screen, color, self.input_rect, border_radius=4)

            # Vẽ text trong input box
            text_surface = self.font.render(self.popup_input_text, True, TEXT_COLOR)
            self.screen.blit(text_surface, (self.input_rect.x + 5, self.input_rect.y + 5))
            y_pos += 60

        # --- NÚT BẮT ĐẦU TRAINING (NEW) ---
        train_rect = pygame.Rect(PANEL_START_X, y_pos, SIDEBAR_WIDTH - 40, BUTTON_HEIGHT)
        train_text = "BẮT ĐẦU HUẤN LUYỆN AI"

        if self.is_training:
            # Vô hiệu hóa nút khi đang training
            self.draw_button(train_rect, f"ĐANG HUẤN LUYỆN...", color=(80, 80, 80))
        else:
            buttons.append(('start_training', self.draw_button(train_rect, train_text, color=ACCENT_COLOR)))

        y_pos += BUTTON_HEIGHT + BUTTON_MARGIN * 3

        # Nút TÀI LIỆU/THÔNG TIN
        info_rect = pygame.Rect(PANEL_START_X, WINDOW_HEIGHT - BUTTON_HEIGHT - BUTTON_MARGIN, SIDEBAR_WIDTH - 40,
                                BUTTON_HEIGHT)
        buttons.append(('info', self.draw_button(info_rect, "Thông Tin", color=BUTTON_COLOR)))

        return buttons

    def draw_game_panel(self):
        """Vẽ thanh bên phải với thông tin trò chơi VÀ các nút điều khiển khi đang chơi."""
        sidebar_rect = pygame.Rect(BOARD_SIZE, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, PANEL_COLOR, sidebar_rect)

        buttons = []
        y_pos = 20

        # I. HEADER VÀ STATUS
        if self.is_training:
            title = self.title_font.render("HUẤN LUYỆN AI", True, (255, 165, 0))
        else:
            title = self.title_font.render("VÁN CỜ", True, ACCENT_COLOR)

        self.screen.blit(title, (PANEL_START_X, y_pos))
        y_pos += 45

        # Lượt đi hiện tại (Chỉ hiển thị nếu KHÔNG phải Training)
        if not self.is_training:
            turn_text = "TRẮNG" if self.board_manager.board.turn == chess.WHITE else "ĐEN"
            turn_color = (255, 255, 255) if self.board_manager.board.turn == chess.WHITE else (100, 100, 100)

            self.screen.blit(self.font.render("LƯỢT:", True, TEXT_COLOR), (PANEL_START_X, y_pos))
            self.screen.blit(self.font.render(turn_text, True, turn_color), (PANEL_START_X + 100, y_pos))
            y_pos += 30

            # Trạng thái trò chơi
            status_text = "Đang Chơi"
            if self.board_manager.board.is_checkmate():
                status_text = "CHIẾU HẾT!"
            elif self.board_manager.board.is_stalemate():
                status_text = "Hòa - Hết nước đi"
            elif self.board_manager.board.is_check():
                status_text = "Chiếu!"

            self.screen.blit(self.font.render(f"Trạng thái: {status_text}", True, TEXT_COLOR), (PANEL_START_X, y_pos))
            y_pos += 30

        # Thông tin AI vs AI series hoặc Training
        if self.is_training:
            # THÔNG TIN TRAINING
            series_info = self.training_game_info
            series_text = self.font.render(series_info, True, (255, 165, 0))
            self.screen.blit(series_text, (PANEL_START_X, y_pos))
            y_pos += 30

            status_text = self.small_font.render(f"Trạng thái: {self.training_status}", True, TEXT_COLOR)
            self.screen.blit(status_text, (PANEL_START_X, y_pos))
            y_pos += 40
        elif self.is_ai_vs_ai_series:
            # THÔNG TIN AI VS AI SERIES
            series_info = f"Ván {self.ai_vs_ai_current_game}/{self.ai_vs_ai_games}"
            series_text = self.font.render(series_info, True, ACCENT_COLOR)
            self.screen.blit(series_text, (PANEL_START_X, y_pos))
            y_pos += 30

            results_info = (
                f"KQ Series: Trắng {self.ai_vs_ai_results['white_wins']} - "
                f"Đen {self.ai_vs_ai_results['black_wins']} - "
                f"Hòa {self.ai_vs_ai_results['draws']}"
            )
            results_text = self.small_font.render(results_info, True, TEXT_COLOR)
            self.screen.blit(results_text, (PANEL_START_X, y_pos))
            y_pos += 40
        else:
            # Thống kê hiệu suất (Chỉ cho Human vs AI)
            stats_text = f"Tỉ lệ thắng: {self.performance_stats.get('win_rate', 0.0):.1f}%"
            self.screen.blit(self.font.render(stats_text, True, TEXT_COLOR), (PANEL_START_X, y_pos))
            y_pos += 40

        pygame.draw.line(self.screen, (80, 80, 95), (BOARD_SIZE + 10, y_pos), (WINDOW_WIDTH - 10, y_pos), 1)
        y_pos += 15

        # II. KHU VỰC NÚT ĐIỀU KHIỂN

        # Nút VÁN MỚI (RESET)
        reset_rect = pygame.Rect(PANEL_START_X, y_pos, SIDEBAR_WIDTH - 40, BUTTON_HEIGHT)
        # Vô hiệu hóa nút RESET khi đang training
        if self.is_training:
            self.draw_button(reset_rect, "VÁN MỚI (Vô hiệu hóa)", color=(80, 80, 80))

            # Thay nút UNDO bằng nút STOP TRAINING
            stop_train_rect = pygame.Rect(PANEL_START_X, y_pos + BUTTON_HEIGHT + BUTTON_MARGIN, SIDEBAR_WIDTH - 40,
                                          BUTTON_HEIGHT)
            buttons.append(('stop_training', self.draw_button(stop_train_rect, "DỪNG HUẤN LUYỆN", color=(255, 0, 0))))

            y_pos += 2 * (BUTTON_HEIGHT + BUTTON_MARGIN)  # Dịch xuống 2 hàng nút

        else:
            buttons.append(('reset', self.draw_button(reset_rect, "VÁN MỚI (RESET)", color=WIN_COLOR)))
            y_pos += BUTTON_HEIGHT + BUTTON_MARGIN

            # Nút HOÀN TÁC (UNDO)
            undo_rect = pygame.Rect(PANEL_START_X, y_pos, SIDEBAR_WIDTH - 40, BUTTON_HEIGHT)
            buttons.append(('undo', self.draw_button(undo_rect, "Hoàn Tác (UNDO)", color=BUTTON_COLOR)))
            y_pos += BUTTON_HEIGHT + BUTTON_MARGIN

        # Nút CHUYỂN CHẾ ĐỘ & PHÂN TÍCH (2 nút ngang)
        btn_width = (SIDEBAR_WIDTH - 50) // 2
        x_start = PANEL_START_X

        mode_text = "AI vs AI" if self.current_player_mode == "human_vs_ai" else "Người vs AI"
        mode_rect = pygame.Rect(x_start, y_pos, btn_width, BUTTON_HEIGHT)
        # Vô hiệu hóa các nút này khi đang training
        if self.is_training:
            self.draw_button(mode_rect, f"Chuyển Chế Độ", color=(80, 80, 80))
        else:
            buttons.append(('switch_mode', self.draw_button(mode_rect, f"Chơi {mode_text}", color=BUTTON_COLOR)))

        x_start += btn_width + 10

        analyze_rect = pygame.Rect(x_start, y_pos, btn_width, BUTTON_HEIGHT)
        if self.is_training:
            self.draw_button(analyze_rect, "Phân Tích", color=(80, 80, 80))
        else:
            buttons.append(('analyze', self.draw_button(analyze_rect, "Phân Tích", color=BUTTON_COLOR)))

        y_pos += BUTTON_HEIGHT + BUTTON_MARGIN

        # KHU VỰC CHỌN ĐỘ KHÓ
        difficulty_label = self.small_font.render("ĐỘ KHÓ:", True, TEXT_COLOR)
        self.screen.blit(difficulty_label, (PANEL_START_X, y_pos))
        y_pos += 20

        btn_width = (SIDEBAR_WIDTH - 50) // 3
        x_start = PANEL_START_X
        difficulties = [('DỄ', 'EASY'), ('TB', 'MEDIUM'), ('KHÓ', 'HARD')]

        for text, level in difficulties:
            diff_rect = pygame.Rect(x_start, y_pos, btn_width, BUTTON_HEIGHT)
            is_active = self.difficulty == level

            if self.is_training:
                self.draw_button(diff_rect, text, is_active=is_active, color=(80, 80, 80))
            else:
                buttons.append((f'set_difficulty_{level}', self.draw_button(diff_rect, text, is_active=is_active)))
            x_start += btn_width + 5

        y_pos += BUTTON_HEIGHT + BUTTON_MARGIN + 10

        # III. KHU VỰC THÔNG TIN (Phân tích/Lịch sử)
        pygame.draw.line(self.screen, (80, 80, 95), (BOARD_SIZE + 10, y_pos), (WINDOW_WIDTH - 10, y_pos), 1)
        y_pos += 10

        # A. Hiển thị kết quả phân tích (Chỉ khi không training)
        if not self.is_training:
            analysis_label = self.small_font.render("PHÂN TÍCH:", True, ACCENT_COLOR)
            self.screen.blit(analysis_label, (PANEL_START_X, y_pos))
            y_pos += 20

            analysis_text = self.game_logic.get_analysis_display() if self.game_logic else "Không thể phân tích."

            # Chia text thành các dòng
            analysis_lines = analysis_text.split('\n')
            for line in analysis_lines[:6]:  # Chỉ hiện 6 dòng đầu
                if y_pos < WINDOW_HEIGHT - 120:
                    text_surface = self.small_font.render(line, True, TEXT_COLOR)
                    self.screen.blit(text_surface, (PANEL_START_X, y_pos))
                    y_pos += 18

            pygame.draw.line(self.screen, (80, 80, 95), (BOARD_SIZE + 10, y_pos), (WINDOW_WIDTH - 10, y_pos), 1)
            y_pos += 10

        # B. LỊCH SỬ NƯỚC ĐI
        history_label = self.small_font.render("LỊCH SỬ NƯỚC ĐI:", True, ACCENT_COLOR)
        self.screen.blit(history_label, (PANEL_START_X, y_pos))
        y_pos += 20

        # Hiển thị 10 nước đi gần nhất từ list history
        moves_to_display = self.game_history_display[-10:]

        # Dàn thành 2 cột: (1. e4 | 1... e5)
        move_history_columns = []
        # Index của nước đi đầu tiên trong moves_to_display (để hiển thị số thứ tự đúng)
        start_index = len(self.board_manager.board.move_stack) - len(moves_to_display)

        for i in range(0, len(moves_to_display), 2):
            white_move_idx = start_index + i
            black_move_idx = start_index + i + 1

            move_number = (white_move_idx // 2) + 1

            white_move_log = moves_to_display[i]
            black_move_log = moves_to_display[i + 1] if i + 1 < len(moves_to_display) else ""

            # Chỉ hiển thị phần nước đi sau số thứ tự
            w_text = white_move_log.split('. ')[-1]
            b_text = black_move_log.split('. ')[-1]

            move_history_columns.append((f"{move_number}. {w_text}", b_text))

        # Vẽ các cặp nước đi
        for white_move, black_move in move_history_columns:
            if y_pos < WINDOW_HEIGHT - 20:
                # Cột Trắng
                text_w = self.small_font.render(white_move, True, TEXT_COLOR)
                self.screen.blit(text_w, (PANEL_START_X, y_pos))

                # Cột Đen (Dịch sang phải)
                text_b = self.small_font.render(black_move, True, TEXT_COLOR)
                self.screen.blit(text_b, (PANEL_START_X + SIDEBAR_WIDTH // 2, y_pos))

                y_pos += 18

        return buttons

    # --- PHƯƠNG THỨC XỬ LÝ SỰ KIỆN ---

    def handle_board_click(self, square):
        """Xử lý click chuột lên bàn cờ."""
        # Không xử lý click nếu đang ở chế độ AI vs AI hoặc Training
        if self.game_mode != "human_vs_ai": return

        if self.selected_square is None:
            # Chọn quân
            piece = self.board_manager.board.piece_at(square)
            # Chỉ cho phép chọn quân cùng màu với lượt hiện tại VÀ cùng màu với người chơi
            if piece and (piece.color == self.board_manager.board.turn) and (piece.color == self.human_color):
                self.selected_square = square
                # Cập nhật valid_moves
                self.valid_moves = [move.to_square for move in self.board_manager.board.legal_moves if
                                    move.from_square == square]
        else:
            # Thực hiện nước đi
            move = chess.Move(self.selected_square, square)

            # Xử lý phong cấp (Giả định luôn phong cấp Hậu 'q' nếu không có UI chọn)
            if self.board_manager.board.piece_at(self.selected_square).piece_type == chess.PAWN and \
                    (square >= chess.A8 or square <= chess.H1) and \
                    not move.promotion:
                move = chess.Move(self.selected_square, square, promotion=chess.QUEEN)

            if self.board_manager.is_valid_move(move):
                move_uci = move.uci()
                move_number = (len(self.board_manager.board.move_stack) // 2) + 1
                log_entry = f"{move_number}. {'Trắng' if self.board_manager.board.turn == chess.WHITE else 'Đen'}: {move_uci}"

                with self.board_lock:
                    self.board_manager.make_move(move)
                    self.last_move = move_uci
                    self.game_history_display.append(log_entry)  # <--- Cập nhật lịch sử cho Human move

                # Cập nhật thống kê nếu thắng/thua
                if self.board_manager.board.is_game_over():
                    result = self.board_manager.board.result()
                    is_human_win = (result == "1-0" and self.human_color == chess.WHITE) or \
                                   (result == "0-1" and self.human_color == chess.BLACK)
                    is_draw = result == "1/2-1/2"

                    if is_draw:
                        self._update_performance_stats('draw')
                    else:
                        self._update_performance_stats(is_human_win)

            self.selected_square = None
            self.valid_moves = []

    def handle_click(self, pos):
        """Xử lý sự kiện click chuột, ưu tiên các nút chức năng."""
        x, y = pos

        # 1. Xử lý click vào input box (chỉ ở menu và khi chọn AI vs AI)
        if self.game_mode == "menu" and self.current_player_mode == "ai_vs_ai" and self.input_rect.collidepoint(pos):
            self.input_active = True
        else:
            self.input_active = False

        # 2. Xử lý click vào các nút chức năng
        for action, rect in self.active_buttons:
            if rect.collidepoint(pos):
                if self.game_mode == "menu":
                    if action == 'start_game':
                        self.game_mode = self.current_player_mode
                        self.reset_game()
                    elif action == 'start_training':  # <-- Xử lý nút Training
                        self.start_training_series()
                    elif action == 'set_mode_human':
                        self.current_player_mode = "human_vs_ai"
                    elif action == 'set_mode_ai':
                        self.current_player_mode = "ai_vs_ai"
                    elif action.startswith('set_difficulty_menu_'):
                        level = action.split('_')[-1]
                        self.set_difficulty(level)
                else:
                    if action == 'reset':
                        if not self.is_training: self.reset_game()  # Chỉ reset khi không training
                    elif action == 'stop_training':  # <-- Nút Dừng Training
                        if self.training_thread and self.training_thread.is_alive():
                            self.training_thread.stop()
                            # join sẽ xảy ra trong run_game_loop
                    elif action == 'undo':
                        if not self.is_training:
                            if self.board_manager.undo_move():
                                if self.game_history_display:
                                    self.game_history_display.pop()
                                try:
                                    self.last_move = self.board_manager.board.peek().uci()
                                except IndexError:
                                    self.last_move = None

                    elif action == 'switch_mode':
                        if not self.is_training: self.switch_game_mode()
                    elif action == 'analyze':
                        if not self.is_training: self.trigger_analysis()
                    elif action.startswith('set_difficulty_'):
                        if not self.is_training:
                            level = action.split('_')[-1]
                            self.set_difficulty(level)
                return

                # 3. Xử lý click vào bàn cờ
        if x < BOARD_SIZE:
            square = self.coords_to_square(x, y)
            if square is not None and not self.ai_thinking and not self.is_training:
                self.handle_board_click(square)

    def handle_events(self):
        """Xử lý tất cả các sự kiện Pygame."""
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                self.running = False
                self.stop_ai_vs_ai.set()  # Dừng worker thread
                if self.training_thread and self.training_thread.is_alive():
                    self.training_thread.stop()

            if event.type == MOUSEBUTTONDOWN:
                self.handle_click(event.pos)

            # Xử lý nhập liệu cho input box (Số ván AI vs AI)
            if self.input_active and event.type == KEYDOWN:
                if event.key == K_RETURN:
                    self.input_active = False
                elif event.key == K_BACKSPACE:
                    self.popup_input_text = self.popup_input_text[:-1]
                    if not self.popup_input_text:
                        self.popup_input_text = "1"  # Không cho rỗng
                else:
                    # Chỉ chấp nhận số
                    if event.unicode.isdigit():
                        new_text = self.popup_input_text + event.unicode
                        try:
                            num = int(new_text)
                            if 1 <= num <= 100 and len(new_text) <= 3:
                                self.popup_input_text = new_text
                        except ValueError:
                            pass

            # Xử lý sự kiện cập nhật UI từ thread
            if event.type == USEREVENT_UPDATE_UI:
                # Không cần làm gì nhiều, chỉ cần sự kiện được nhận để vòng lặp chính chạy lại
                pass

    # --- PHƯƠNG THỨC DI CHUYỂN AI ---

    def ai_move_async(self):
        """Hàm bất đồng bộ cho AI tính toán và thực hiện nước đi (chế độ Human vs AI)."""
        try:
            current_board = self.board_manager.board.copy()

            if self.ai_engine:
                move, score = self.ai_engine.get_best_move(current_board)
            else:
                legal_moves = list(current_board.legal_moves)
                move = random.choice(legal_moves) if legal_moves else None

            if move:
                move_uci = move.uci()
                move_number = (len(self.board_manager.board.move_stack) // 2) + 1
                log_entry = f"{move_number}. {'Trắng' if current_board.turn == chess.WHITE else 'Đen'}: {move_uci}"
                print(f"[Human vs AI] {log_entry}")  # Log cho chế độ người chơi

                with self.board_lock:
                    if self.board_manager.is_valid_move(move):
                        self.board_manager.make_move(move)
                        self.last_move = move_uci
                        self.game_history_display.append(log_entry)  # <--- Cập nhật lịch sử

                # Cập nhật thống kê nếu thắng/thua
                if self.board_manager.board.is_game_over():
                    result = self.board_manager.board.result()
                    is_human_win = (result == "1-0" and self.human_color == chess.WHITE) or \
                                   (result == "0-1" and self.human_color == chess.BLACK)
                    is_draw = result == "1/2-1/2"

                    if is_draw:
                        self._update_performance_stats('draw')
                    else:
                        self._update_performance_stats(is_human_win)


            else:
                print("AI không tìm được nước đi hợp lệ.")

        except Exception as e:
            print(f"Lỗi khi AI di chuyển: {e}")
        finally:
            self.ai_thinking = False

    def start_ai_vs_ai_series(self):
        """Chuẩn bị và bắt đầu series AI vs AI."""
        # ... (Logic chuẩn bị series) ...
        self.ai_vs_ai_log_moves = []
        self.ai_vs_ai_game_result = None
        self.ai_vs_ai_running = True
        self.ai_vs_ai_current_log = "Ván đấu bắt đầu..."
        self.ai_vs_ai_current_game = 1  # Hoặc logic series của bạn

        # Bắt đầu thread chính chạy game
        self.ai_vs_ai_thread = threading.Thread(target=self.ai_vs_ai_game_loop, daemon=True)
        self.ai_vs_ai_thread.start()
    # --- PHƯƠNG THỨC VẼ BÀN CỜ ---

    def draw_board_and_pieces(self, screen):
        """Vẽ bàn cờ, quân cờ, highlight, và nước đi cuối."""
        with self.board_lock:
            if draw_chess_board:
                draw_chess_board(screen, self.board_manager.board, SQUARE_SIZE)
            else:
                # Fallback: Vẽ bàn cờ đơn giản
                for r in range(8):
                    for c in range(8):
                        color = (181, 136, 99) if (r + c) % 2 == 0 else (240, 217, 181)
                        pygame.draw.rect(screen, color, (c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

            # Highlight nước đi cuối cùng
            if self.last_move:
                try:
                    from_sq = chess.parse_square(self.last_move[:2])
                    to_sq = chess.parse_square(self.last_move[2:4])

                    for square in [from_sq, to_sq]:
                        col = square % 8
                        row = 7 - (square // 8)
                        last_move_rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                        s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                        s.fill(LAST_MOVE)
                        screen.blit(s, last_move_rect)
                except:
                    # Bỏ qua nếu last_move không phải là uci hợp lệ (có thể là None)
                    pass

            # Highlight ô được chọn
            if self.selected_square is not None:
                col = self.selected_square % 8
                row = 7 - (self.selected_square // 8)
                highlight_rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                s.fill(HIGHLIGHT)
                screen.blit(s, highlight_rect)

            # Highlight nước đi hợp lệ
            for square in self.valid_moves:
                col = square % 8
                row = 7 - (square // 8)
                # Vẽ chấm tròn thay vì tô màu toàn bộ ô
                center_x = col * SQUARE_SIZE + SQUARE_SIZE // 2
                center_y = row * SQUARE_SIZE + SQUARE_SIZE // 2

                # Kiểm tra nếu ô là nơi quân bị ăn, vẽ vòng tròn thay vì chấm tròn
                if self.board_manager.board.piece_at(square):
                    pygame.draw.circle(screen, VALID_MOVE, (center_x, center_y), SQUARE_SIZE // 2, 4)
                else:
                    pygame.draw.circle(screen, VALID_MOVE, (center_x, center_y), SQUARE_SIZE // 6)

            # Highlight vua bị chiếu
            if self.board_manager.board.is_check():
                king_square = self.board_manager.board.king(self.board_manager.board.turn)
                if king_square is not None:
                    col = king_square % 8
                    row = 7 - (king_square // 8)
                    check_rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                    s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    s.fill(CHECK_COLOR)
                    screen.blit(s, check_rect)

    # --- VÒNG LẶP CHÍNH ---

    def run_game_loop(self):
        while self.running:
            # Xử lý input
            self.handle_events()

            # Xóa màn hình
            self.screen.fill(BG_COLOR)

            # VẼ BÀN CỜ
            self.draw_board_and_pieces(self.screen)

            # VẼ UI DỰA TRÊN CHẾ ĐỘ
            if self.game_mode == "menu":
                self.active_buttons = self.draw_menu()
            else:
                self.active_buttons = self.draw_game_panel()

                # Logic cập nhật trạng thái UI từ Training Thread
            if self.is_training and self.training_thread:
                if self.training_thread.is_alive():
                    # Cập nhật status và progress từ thread vào GUI
                    self.training_status = self.training_thread.status
                    self.training_progress = self.training_thread.progress
                else:
                    # Nếu thread đã kết thúc (dù thành công hay thất bại), dọn dẹp
                    self.training_thread.join()
                    self.is_training = False

                    # Logic AI (chỉ chạy khi Human vs AI VÀ đến lượt AI)
            is_ai_turn = self.game_mode == "human_vs_ai" and self.board_manager.board.turn != self.human_color

            # Hiện trạng thái AI đang tính toán (Cũng dùng cho AI vs AI)
            if self.ai_thinking:
                thinking_text = self.font.render("AI Đang Tính Toán...", True, ACCENT_COLOR)
                self.screen.blit(thinking_text, (BOARD_SIZE + 20, 160))

            # Không chạy AI trong loop nếu đang training
            if is_ai_turn and not self.ai_thinking and not self.board_manager.board.is_game_over() and not self.is_training:
                self.ai_thinking = True
                threading.Thread(target=self.ai_move_async, daemon=True).start()

            pygame.display.flip()
            self.clock.tick(FPS)

        # Đóng Pygame và dừng thread khi thoát
        self.stop_ai_vs_ai.set()
        if self.training_thread and self.training_thread.is_alive():
            self.training_thread.stop()
        pygame.quit()
        sys.exit()


if __name__ == '__main__':
    ui = ChessGUI()
    ui.run_game_loop()