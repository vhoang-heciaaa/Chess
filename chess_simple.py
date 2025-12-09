# ================================
# CÁC BIẾN CHUNG CHO GAME CỜ VUA
# ================================

# ----- KÍCH THƯỚC -----
WIDTH = 640          # chiều rộng cửa sổ
HEIGHT = 640         # chiều cao
ROWS = 8             # số hàng bàn cờ
COLS = 8             # số cột bàn cờ
SQ = WIDTH // COLS   # kích thước 1 ô (80px)

# ----- MÀU SẮC Ô -----
WHITE_SQUARE = (240, 217, 181)
BROWN_SQUARE = (181, 136, 99)

# ----- QUÂN CỜ UNICODE -----
PIECES = {
    "r": "♜", "n": "♞", "b": "♝", "q": "♛", "k": "♚", "p": "♟",
    "R": "♖", "N": "♘", "B": "♗", "Q": "♕", "K": "♔", "P": "♙"
}

# ----- BÀN CỜ BAN ĐẦU -----
DEFAULT_BOARD = [
    ["r","n","b","q","k","b","n","r"],
    ["p","p","p","p","p","p","p","p"],
    ["","","","","","","",""],
    ["","","","","","","",""],
    ["","","","","","","",""],
    ["","","","","","","",""],
    ["P","P","P","P","P","P","P","P"],
    ["R","N","B","Q","K","B","N","R"]
]

# ----- BIẾN TRẠNG THÁI -----
selected_piece = None     # (row, col) quân đang được chọn
current_turn = "white"    # lượt chơi hiện tại
valid_moves = []  #nước đi hợp lệ
