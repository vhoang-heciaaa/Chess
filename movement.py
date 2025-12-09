import pygame
from chess_simple_data.chess_simple import SQ
from chess_simple_data.rule import get_valid_moves, make_move

def handle_click(board, position, selected, current_turn, valid_moves):
    row, col = position

    if selected is None:
        if board[row][col] != "":
            piece = board[row][col]
            if (current_turn == "white" and piece.isupper()) or (current_turn == "black" and piece.islower()):
                selected = (row, col)
                # Xóa dòng import bên trong hàm
                valid_moves = get_valid_moves(board, selected, current_turn)
    else:
        if (row, col) in valid_moves:
            # Xóa dòng import bên trong hàm
            success, new_turn = make_move(board, selected, (row, col), current_turn)
            if success:
                current_turn = new_turn

        selected = None
        valid_moves = []

        if board[row][col] != "":
            piece = board[row][col]
            if (current_turn == "white" and piece.isupper()) or (current_turn == "black" and piece.islower()):
                selected = (row, col)
                # Xóa dòng import bên trong hàm
                valid_moves = get_valid_moves(board, selected, current_turn)

    return selected, current_turn, valid_moves