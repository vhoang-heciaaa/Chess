import pygame
import time
from chess_simple import WIDTH, HEIGHT, SQ


class GameState:
    def __init__(self):
        self.current_turn = "white"
        self.white_time = 600  # 10 phút = 600 giây
        self.black_time = 600
        self.white_score = 0
        self.black_score = 0
        self.captured_pieces = {"white": [], "black": []}  # Quân bị ăn
        self.start_time = time.time()
        self.last_update = time.time()

    def switch_turn(self):
        """Chuyển lượt và cập nhật thời gian"""
        current_time = time.time()
        elapsed = current_time - self.last_update

        if self.current_turn == "white":
            self.white_time -= elapsed
        else:
            self.black_time -= elapsed

        self.current_turn = "black" if self.current_turn == "white" else "white"
        self.last_update = current_time

    def add_captured_piece(self, piece, captor_color):
        """Thêm quân bị ăn vào danh sách và tính điểm"""
        piece_value = {
            'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0,
            'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0
        }

        value = piece_value.get(piece, 0)
        self.captured_pieces[captor_color].append(piece)

        if captor_color == "white":
            self.white_score += value
        else:
            self.black_score += value

    def update_time(self):
        """Cập nhật thời gian cho lượt hiện tại"""
        current_time = time.time()
        elapsed = current_time - self.last_update

        if self.current_turn == "white":
            self.white_time -= elapsed
        else:
            self.black_time -= elapsed

        self.last_update = current_time

    def format_time(self, seconds):
        """Định dạng thời gian MM:SS"""
        if seconds <= 0:
            return "00:00"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def is_time_up(self):
        """Kiểm tra hết giờ"""
        return self.white_time <= 0 or self.black_time <= 0

    def get_winner(self):
        """Xác định người thắng khi hết giờ"""
        if self.white_time <= 0:
            return "black"
        elif self.black_time <= 0:
            return "white"
        return None


def draw_game_state(screen, game_state):
    """Vẽ bảng trạng thái game"""
    # Tạo surface cho bảng trạng thái
    panel_width = 200
    panel_height = HEIGHT
    panel_x = WIDTH
    panel = pygame.Surface((panel_width, panel_height))
    panel.fill((50, 50, 50))  # Màu nền xám đậm

    # Font chữ
    title_font = pygame.font.SysFont('arial', 24, bold=True)
    normal_font = pygame.font.SysFont('arial', 18)
    small_font = pygame.font.SysFont('arial', 14)

    # Tiêu đề - SỬA CHÍNH TẢ
    title = title_font.render("TRẠNG THÁI GAME", True, (255, 255, 255))
    panel.blit(title, (10, 20))

    # Lượt hiện tại - SỬA CHÍNH TẢ
    turn_text = f"Lượt: {'TRẮNG' if game_state.current_turn == 'white' else 'ĐEN'}"
    turn_color = (255, 255, 255) if game_state.current_turn == "white" else (200, 200, 200)
    turn_surface = normal_font.render(turn_text, True, turn_color)
    panel.blit(turn_surface, (10, 60))

    # Thời gian - SỬA CHÍNH TẢ
    y_pos = 100
    time_section = normal_font.render("THỜI GIAN:", True, (255, 255, 255))
    panel.blit(time_section, (10, y_pos))

    white_time = game_state.format_time(game_state.white_time)
    black_time = game_state.format_time(game_state.black_time)

    white_time_text = normal_font.render(f"Trắng: {white_time}", True, (255, 255, 255))
    black_time_text = normal_font.render(f"Đen: {black_time}", True, (200, 200, 200))

    panel.blit(white_time_text, (20, y_pos + 30))
    panel.blit(black_time_text, (20, y_pos + 60))

    # Điểm số - SỬA CHÍNH TẢ
    y_pos += 120
    score_section = normal_font.render("ĐIỂM SỐ:", True, (255, 255, 255))
    panel.blit(score_section, (10, y_pos))

    white_score = normal_font.render(f"Trắng: {game_state.white_score}", True, (255, 255, 255))
    black_score = normal_font.render(f"Đen: {game_state.black_score}", True, (200, 200, 200))

    panel.blit(white_score, (20, y_pos + 30))
    panel.blit(black_score, (20, y_pos + 60))

    # Quân đã ăn - SỬA CHÍNH TẢ
    y_pos += 120
    captured_section = normal_font.render("QUÂN ĐÃ ĂN:", True, (255, 255, 255))
    panel.blit(captured_section, (10, y_pos))

    # Quân trắng đã ăn
    white_captured = small_font.render("Trắng ăn:", True, (255, 255, 255))
    panel.blit(white_captured, (10, y_pos + 30))

    captured_text = " ".join(game_state.captured_pieces["white"])
    if not captured_text:
        captured_text = "Không có"
    white_pieces = small_font.render(captured_text, True, (200, 200, 200))
    panel.blit(white_pieces, (10, y_pos + 50))

    # Quân đen đã ăn
    black_captured = small_font.render("Đen ăn:", True, (200, 200, 200))
    panel.blit(black_captured, (10, y_pos + 80))

    captured_text = " ".join(game_state.captured_pieces["black"])
    if not captured_text:
        captured_text = "Không có"
    black_pieces = small_font.render(captured_text, True, (200, 200, 200))
    panel.blit(black_pieces, (10, y_pos + 100))

    # Vẽ panel lên screen
    screen.blit(panel, (panel_x, 0))


def create_game_state():
    """Tạo đối tượng game state mới"""
    return GameState()