# ================================
# LUẬT DI CHUYỂN CÁC QUÂN CỜ VUA
# ================================

def is_valid_move(board, start_pos, end_pos, current_turn):
    """
    Kiểm tra nước đi có hợp lệ không
    """
    start_row, start_col = start_pos
    end_row, end_col = end_pos

    # Kiểm tra ô bắt đầu có quân cờ không
    if not board[start_row][start_col]:
        return False

    # Kiểm tra quân cờ có thuộc lượt hiện tại không
    piece = board[start_row][start_col]
    if (current_turn == "white" and piece.islower()) or (current_turn == "black" and piece.isupper()):
        return False

    # Kiểm tra ô kết thúc không có quân cờ cùng màu
    if board[end_row][end_col]:
        target_piece = board[end_row][end_col]
        if (current_turn == "white" and target_piece.isupper()) or (current_turn == "black" and target_piece.islower()):
            return False

    # Kiểm tra luật di chuyển theo từng loại quân
    piece_type = piece.lower()

    if piece_type == "p":  # Tốt
        return is_valid_pawn_move(board, start_pos, end_pos, current_turn)
    elif piece_type == "r":  # Xe
        return is_valid_rook_move(board, start_pos, end_pos)
    elif piece_type == "n":  # Mã
        return is_valid_knight_move(start_pos, end_pos)
    elif piece_type == "b":  # Tượng
        return is_valid_bishop_move(board, start_pos, end_pos)
    elif piece_type == "q":  # Hậu
        return is_valid_queen_move(board, start_pos, end_pos)
    elif piece_type == "k":  # Vua
        return is_valid_king_move(start_pos, end_pos)

    return False


def is_valid_pawn_move(board, start_pos, end_pos, current_turn):
    """
    Luật di chuyển cho quân Tốt
    """
    start_row, start_col = start_pos
    end_row, end_col = end_pos
    piece = board[start_row][start_col]

    direction = -1 if current_turn == "white" else 1  # Trắng đi lên, đen đi xuống
    start_row_pawn = 6 if current_turn == "white" else 1  # Hàng xuất phát

    # Di chuyển thẳng
    if start_col == end_col:
        # Di chuyển 1 ô
        if end_row == start_row + direction and not board[end_row][end_col]:
            return True
        # Di chuyển 2 ô từ vị trí xuất phát
        if (start_row == start_row_pawn and
                end_row == start_row + 2 * direction and
                not board[end_row][end_col] and
                not board[start_row + direction][start_col]):
            return True

    # Ăn quân chéo
    if (abs(start_col - end_col) == 1 and
            end_row == start_row + direction and
            board[end_row][end_col]):
        return True

    return False


def is_valid_rook_move(board, start_pos, end_pos):
    """
    Luật di chuyển cho quân Xe
    """
    start_row, start_col = start_pos
    end_row, end_col = end_pos

    # Chỉ di chuyển ngang hoặc dọc
    if start_row != end_row and start_col != end_col:
        return False

    # Kiểm tra đường đi không bị chặn
    if start_row == end_row:  # Di chuyển ngang
        step = 1 if end_col > start_col else -1
        for col in range(start_col + step, end_col, step):
            if board[start_row][col]:
                return False
    else:  # Di chuyển dọc
        step = 1 if end_row > start_row else -1
        for row in range(start_row + step, end_row, step):
            if board[row][start_col]:
                return False

    return True


def is_valid_knight_move(start_pos, end_pos):
    """
    Luật di chuyển cho quân Mã
    """
    start_row, start_col = start_pos
    end_row, end_col = end_pos

    # Mã di chuyển theo hình chữ L
    row_diff = abs(start_row - end_row)
    col_diff = abs(start_col - end_col)

    return (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)


def is_valid_bishop_move(board, start_pos, end_pos):
    """
    Luật di chuyển cho quân Tượng
    """
    start_row, start_col = start_pos
    end_row, end_col = end_pos

    # Chỉ di chuyển chéo
    if abs(start_row - end_row) != abs(start_col - end_col):
        return False

    # Kiểm tra đường đi không bị chặn
    row_step = 1 if end_row > start_row else -1
    col_step = 1 if end_col > start_col else -1

    steps = abs(start_row - end_row)
    for i in range(1, steps):
        check_row = start_row + i * row_step
        check_col = start_col + i * col_step
        if board[check_row][check_col]:
            return False

    return True


def is_valid_queen_move(board, start_pos, end_pos):
    """
    Luật di chuyển cho quân Hậu (kết hợp Xe và Tượng)
    """
    return (is_valid_rook_move(board, start_pos, end_pos) or
            is_valid_bishop_move(board, start_pos, end_pos))


def is_valid_king_move(start_pos, end_pos):
    """
    Luật di chuyển cho quân Vua
    """
    start_row, start_col = start_pos
    end_row, end_col = end_pos

    # Vua di chuyển 1 ô theo mọi hướng
    return abs(start_row - end_row) <= 1 and abs(start_col - end_col) <= 1


def get_valid_moves(board, position, current_turn):
    """
    Lấy tất cả các nước đi hợp lệ cho quân cờ tại vị trí cho trước
    """
    valid_moves = []
    row, col = position

    # Kiểm tra ô có quân cờ không
    if not board[row][col]:
        return valid_moves

    # Kiểm tra quân cờ có thuộc lượt hiện tại không
    piece = board[row][col]
    if (current_turn == "white" and piece.islower()) or (current_turn == "black" and piece.isupper()):
        return valid_moves

    # Duyệt qua tất cả các ô trên bàn cờ
    for end_row in range(8):
        for end_col in range(8):
            end_pos = (end_row, end_col)
            if is_valid_move(board, position, end_pos, current_turn):
                valid_moves.append(end_pos)

    return valid_moves


def make_move(board, start_pos, end_pos, current_turn):
    """
    Thực hiện nước đi nếu hợp lệ
    """
    if is_valid_move(board, start_pos, end_pos, current_turn):
        start_row, start_col = start_pos
        end_row, end_col = end_pos

        # Di chuyển quân cờ
        board[end_row][end_col] = board[start_row][start_col]
        board[start_row][start_col] = ""

        # Đổi lượt
        current_turn = "black" if current_turn == "white" else "white"

        return True, current_turn

    return False, current_turn