from chess_simple_data.chess_simple import *
import pygame
import chess

# Sử dụng Unicode characters (giống trong HTML)
HTML_UNICODE_PIECES = {
    "r": "♜", "n": "♞", "b": "♝", "q": "♛", "k": "♚", "p": "♟",
    "R": "♖", "N": "♘", "B": "♗", "Q": "♕", "K": "♔", "P": "♙"
}


def board_to_matrix(board):
    """Chuyển đổi chess.Board sang ma trận 2D"""
    matrix = [[None for _ in range(8)] for _ in range(8)]

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            row = 7 - (square // 8)  # Đảo ngược hàng để hiển thị đúng
            col = square % 8
            matrix[row][col] = piece.symbol()

    return matrix


def draw_chess_board(screen, board, square_size):
    """
    Vẽ bàn cờ và quân cờ từ chess.Board object
    """
    # Khởi tạo font một lần
    if not hasattr(draw_chess_board, 'font'):
        try:
            fonts = ['Segoe UI Symbol', 'Arial Unicode MS', 'DejaVu Sans']
            for font_name in fonts:
                try:
                    draw_chess_board.font = pygame.font.SysFont(font_name, int(square_size * 0.7))
                    break
                except:
                    continue
            else:
                draw_chess_board.font = pygame.font.Font(None, int(square_size * 0.7))
        except:
            draw_chess_board.font = pygame.font.Font(None, int(square_size * 0.7))

    # Chuyển đổi board sang ma trận
    board_matrix = board_to_matrix(board)

    # Vẽ các ô cờ
    for row in range(8):
        for col in range(8):
            color = WHITE_SQUARE if (row + col) % 2 == 0 else BROWN_SQUARE
            pygame.draw.rect(screen, color, (col * square_size, row * square_size, square_size, square_size))

            # Vẽ quân cờ
            piece = board_matrix[row][col]
            if piece and piece in HTML_UNICODE_PIECES:
                piece_char = HTML_UNICODE_PIECES[piece]
                text_color = (0, 0, 0)  # Màu đen

                text = draw_chess_board.font.render(piece_char, True, text_color)
                text_rect = text.get_rect(center=(col * square_size + square_size // 2,
                                                  row * square_size + square_size // 2))
                screen.blit(text, text_rect)


def draw_selection_and_moves(screen, selected, valid_moves, square_size):
    """
    Vẽ ô được chọn và các nước đi hợp lệ
    """
    # Vẽ ô được chọn
    if selected:
        row, col = selected
        pygame.draw.rect(screen, (255, 0, 0),
                         (col * square_size, row * square_size, square_size, square_size), 3)

    # Vẽ các nước đi hợp lệ
    for move in valid_moves:
        row, col = move
        pygame.draw.circle(screen, (0, 255, 0),
                           (col * square_size + square_size // 2,
                            row * square_size + square_size // 2), 8)

def draw_chess_board(screen, board_data, square_size):
    """
    Vẽ bàn cờ và quân cờ, hỗ trợ cả chess.Board object và mảng 2D
    """
    # Khởi tạo font
    if not hasattr(draw_chess_board, 'font'):
        try:
            fonts = ['Segoe UI Symbol', 'Arial Unicode MS', 'DejaVu Sans']
            for font_name in fonts:
                try:
                    draw_chess_board.font = pygame.font.SysFont(font_name, int(square_size * 0.7))
                    break
                except:
                    continue
            else:
                draw_chess_board.font = pygame.font.Font(None, int(square_size * 0.7))
        except:
            draw_chess_board.font = pygame.font.Font(None, int(square_size * 0.7))

    # Xác định kiểu dữ liệu đầu vào
    if isinstance(board_data, chess.Board):
        # Nếu là chess.Board object
        board_matrix = board_to_matrix(board_data)
    elif isinstance(board_data, list) and len(board_data) == 8:
        # Nếu là mảng 2D 8x8
        board_matrix = board_data
    else:
        raise ValueError("Đầu vào phải là chess.Board object hoặc mảng 8x8")

    # Vẽ các ô cờ
    for row in range(8):
        for col in range(8):
            color = WHITE_SQUARE if (row + col) % 2 == 0 else BROWN_SQUARE
            pygame.draw.rect(screen, color, (col * square_size, row * square_size, square_size, square_size))

            # Vẽ quân cờ
            piece = board_matrix[row][col]
            if piece and piece in HTML_UNICODE_PIECES:
                piece_char = HTML_UNICODE_PIECES[piece]
                text_color = (0, 0, 0)  # Màu đen

                text = draw_chess_board.font.render(piece_char, True, text_color)
                text_rect = text.get_rect(center=(col * square_size + square_size // 2,
                                                  row * square_size + square_size // 2))
                screen.blit(text, text_rect)