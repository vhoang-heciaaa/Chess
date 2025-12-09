# Shiro_management.py
import chess
import chess.pgn
import io


class ChessBoardManager:
    def __init__(self, fen=None):
        """
        Khởi tạo bàn cờ
        - fen: Chuỗi FEN để khởi tạo bàn cờ từ trạng thái cụ thể
        """
        print(f"[ChessBoardManager] Khởi tạo với fen: {fen}")

        # ĐẢM BẢO board là chess.Board, không phải list
        try:
            if fen:
                print(f"[ChessBoardManager] Tạo board từ FEN: {fen}")
                self.board = chess.Board(fen)
            else:
                print(f"[ChessBoardManager] Tạo board mới")
                self.board = chess.Board()
        except Exception as e:
            print(f"[ChessBoardManager] Lỗi khi tạo board: {e}")
            # Fallback: luôn tạo board mới
            self.board = chess.Board()

        print(f"[ChessBoardManager] Kiểu board: {type(self.board)}")
        print(f"[ChessBoardManager] Board có piece_at: {hasattr(self.board, 'piece_at')}")

        self.move_history = []
        self.game_result = None

    def is_valid_move(self, move):
        """Kiểm tra nước đi hợp lệ"""
        try:
            # Kiểm tra board hợp lệ
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                print(f"[is_valid_move] Board không hợp lệ: {type(self.board)}")
                return False

            # Hỗ trợ cả chuỗi UCI và đối tượng Move
            if isinstance(move, str):
                move = chess.Move.from_uci(move)
            return move in self.board.legal_moves
        except Exception as e:
            print(f"[is_valid_move] Lỗi: {e}")
            return False

    def make_move(self, move):

        print(f"[make_move] Thực hiện nước đi: {move}")

        # Kiểm tra board hợp lệ
        if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
            print(f"[make_move] Lỗi: Board không hợp lệ! Kiểu: {type(self.board)}")
            return False

        try:
            if isinstance(move, str):
                move = chess.Move.from_uci(move)

            if self.is_valid_move(move):
                self.board.push(move)
                self.move_history.append(move)
                print(f"[make_move] Thành công: {move}")
                return True
            else:
                print(f"[make_move] Nước đi không hợp lệ: {move}")
                return False
        except Exception as e:
            print(f"[make_move] Lỗi khi thực hiện nước đi: {e}")
            return False

    def unmake_move(self):
        """Hoàn tác nước đi cuối cùng"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return None

            if len(self.board.move_stack) > 0:
                move = self.board.pop()
                if self.move_history:
                    self.move_history.pop()
                print(f"[unmake_move] Đã hoàn tác: {move}")
                return move
            return None
        except Exception as e:
            print(f"[unmake_move] Lỗi: {e}")
            return None

    def is_game_over(self):
        """Kiểm tra kết thúc ván cờ"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return False
            return self.board.is_game_over()
        except:
            return False

    def get_game_result(self):
        """Xác định kết quả ván cờ"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return "ERROR - INVALID BOARD"

            if self.board.is_checkmate():
                winner = "WHITE" if self.board.turn == chess.BLACK else "BLACK"
                return f"CHECKMATE - {winner} WINS"
            elif self.board.is_stalemate():
                return "DRAW - STALEMATE"
            elif self.board.is_insufficient_material():
                return "DRAW - INSUFFICIENT MATERIAL"
            elif self.board.is_fifty_moves():
                return "DRAW - FIFTY-MOVE RULE"
            elif self.board.is_repetition():
                return "DRAW - REPETITION"
            return "GAME IN PROGRESS"
        except Exception as e:
            return f"ERROR - {str(e)}"

    def get_winner(self):
        """Xác định người thắng (nếu có)"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return None

            if self.board.is_checkmate():
                return chess.WHITE if self.board.turn == chess.BLACK else chess.BLACK
            return None
        except:
            return None

    def get_current_player(self):
        """Lấy người chơi hiện tại"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return "UNKNOWN"
            return "WHITE" if self.board.turn else "BLACK"
        except:
            return "UNKNOWN"

    def get_legal_moves(self, as_uci=False):
        """Lấy danh sách nước đi hợp lệ"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return []

            moves = list(self.board.legal_moves)
            if as_uci:
                return [move.uci() for move in moves]
            return moves
        except:
            return []

    def get_board_visual(self):
        """Trả về biểu diễn trực quan của bàn cờ (text tree - Unicode)."""
        # Đây là phương thức có sẵn của python-chess
        return self.board.unicode_pretty()

    def get_pgn(self):
        """
        Trả về lịch sử nước đi dưới dạng PGN.
        """
        # Sử dụng board tạm để tạo PGN từ move_history
        temp_board = chess.Board()
        pgn_moves = []
        for i, move_uci in enumerate(self.move_history):
            move = chess.Move.from_uci(move_uci)
            if i % 2 == 0:
                pgn_moves.append(f"{i // 2 + 1}. {temp_board.san(move)}")
            else:
                pgn_moves[-1] += f" {temp_board.san(move)}"
            temp_board.push(move)

        pgn_text = " ".join(pgn_moves)

        # Thêm kết quả ván đấu (nếu có)
        result_map = {'1-0': '1-0', '0-1': '0-1', '1/2-1/2': '1/2-1/2'}
        pgn_text += f" {result_map.get(self.get_game_result(), '*')}"

        return pgn_text

    def get_fen(self):
        """Lấy trạng thái bàn cờ dạng FEN"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return ""
            return self.board.fen()
        except:
            return ""

    def get_castling_rights(self):
        """Lấy thông tin quyền nhập thành"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return {}

            return {
                'white_kingside': self.board.has_kingside_castling_rights(chess.WHITE),
                'white_queenside': self.board.has_queenside_castling_rights(chess.WHITE),
                'black_kingside': self.board.has_kingside_castling_rights(chess.BLACK),
                'black_queenside': self.board.has_queenside_castling_rights(chess.BLACK)
            }
        except:
            return {}

    def get_en_passant_square(self):
        """Lấy ô en passant (nếu có)"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return None

            if self.board.ep_square:
                return chess.square_name(self.board.ep_square)
            return None
        except:
            return None

    def is_check(self):
        """Kiểm tra có đang chiếu tướng không"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return False
            return self.board.is_check()
        except:
            return False

    def get_piece_at(self, square):
        """
        Lấy thông tin quân cờ tại ô
        - square: tên ô (ví dụ: 'e4') hoặc số ô (0-63)
        """
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return None

            if isinstance(square, str):
                square = chess.parse_square(square)

            piece = self.board.piece_at(square)
            if piece:
                return {
                    'symbol': piece.symbol(),
                    'color': 'WHITE' if piece.color else 'BLACK',
                    'type': piece.piece_type,
                    'name': chess.piece_name(piece.piece_type).upper()
                }
            return None
        except Exception as e:
            print(f"[get_piece_at] Lỗi: {e}")
            return None

    def get_piece_count(self):
        """Đếm số quân cờ còn lại trên bàn"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return {'white': {}, 'black': {}}

            white_pieces = {}
            black_pieces = {}

            for piece_type in range(1, 7):  # PAWN đến KING
                white_count = len(self.board.pieces(piece_type, chess.WHITE))
                black_count = len(self.board.pieces(piece_type, chess.BLACK))

                piece_name = chess.piece_name(piece_type).upper()
                white_pieces[piece_name] = white_count
                black_pieces[piece_name] = black_count

            return {'white': white_pieces, 'black': black_pieces}
        except:
            return {'white': {}, 'black': {}}

    def get_move_history(self, as_uci=True):
        """Lấy lịch sử nước đi"""
        try:
            if as_uci:
                return [move.uci() for move in self.move_history]
            return self.move_history
        except:
            return []

    def reset_board(self, fen=None):
        """Reset bàn cờ về trạng thái ban đầu"""
        print(f"[reset_board] Reset board với fen: {fen}")
        try:
            if fen:
                self.board = chess.Board(fen)
            else:
                self.board = chess.Board()
            self.move_history = []
            self.game_result = None
            print(f"[reset_board] Đã reset. Kiểu board mới: {type(self.board)}")
        except Exception as e:
            print(f"[reset_board] Lỗi khi reset: {e}")
            # Fallback
            self.board = chess.Board()
            self.move_history = []
            self.game_result = None

    def export_pgn(self, event="Game", white="Player1", black="Player2"):
        """Xuất ván cờ dạng PGN"""
        try:
            if not hasattr(self, 'board') or not isinstance(self.board, chess.Board):
                return "ERROR: Invalid board"

            game = chess.pgn.Game()
            game.headers["Event"] = event
            game.headers["White"] = white
            game.headers["Black"] = black
            game_result = self.get_game_result().split(" - ")[0]
            game.headers["Result"] = game_result

            node = game
            for move in self.move_history:
                node = node.add_variation(move)

            return str(game)
        except Exception as e:
            return f"ERROR: {str(e)}"

    def get_game_state(self):
        """Lấy toàn bộ trạng thái game dạng dictionary"""
        try:
            return {
                'fen': self.get_fen(),
                'current_player': self.get_current_player(),
                'is_game_over': self.is_game_over(),
                'game_result': self.get_game_result(),
                'is_check': self.is_check(),
                'legal_moves': len(self.get_legal_moves()),
                'castling_rights': self.get_castling_rights(),
                'en_passant': self.get_en_passant_square(),
                'move_count': len(self.move_history),
                'halfmove_clock': self.board.halfmove_clock if hasattr(self.board, 'halfmove_clock') else 0,
                'fullmove_number': self.board.fullmove_number if hasattr(self.board, 'fullmove_number') else 1,
                'piece_count': self.get_piece_count()
            }
        except Exception as e:
            print(f"[get_game_state] Lỗi: {e}")
            return {'error': str(e)}

    def __str__(self):
        """String representation của ChessBoardManager"""
        if hasattr(self, 'board') and isinstance(self.board, chess.Board):
            return f"ChessBoardManager(board={self.board.fen()})"
        return "ChessBoardManager(INVALID)"

    def __repr__(self):
        return self.__str__()

    def undo_move(self):
        """Hoàn tác nước đi cuối cùng."""
        try:
            # Lệnh pop() của thư viện python-chess sẽ hoàn tác nước đi cuối cùng
            self.board.pop()
            if self.move_history:
                # Xóa nước đi cuối khỏi lịch sử (nếu bạn đang dùng move_history để lưu trữ)
                self.move_history.pop()
            return True
        except IndexError:
            # Không có nước đi nào để hoàn tác
            return False
        except Exception as e:
            print(f"[ChessBoardManager] Lỗi khi hoàn tác nước đi: {e}")
            return False

    def get_last_move_log(self):
        """Trả về log của nước đi gần nhất."""
        if not self.move_history:
            return "Chưa có nước đi nào."

        last_move_uci = self.move_history[-1]

        # Tạo board tạm để có thể chuyển đổi UCI sang SAN
        temp_board = chess.Board()

        # Replay tất cả các nước đi trừ nước cuối
        for move_uci in self.move_history[:-1]:
            temp_board.push_uci(move_uci)

        try:
            last_move = chess.Move.from_uci(last_move_uci)
            last_move_san = temp_board.san(last_move)

            # Lượt của quân đi nước này (quân vừa đi)
            is_white_move = len(self.move_history) % 2 != 0  # Nếu số nước đi là lẻ, thì là lượt Trắng đi (1, 3, 5...)
            move_number = (len(self.move_history) + 1) // 2

            color_turn = "Trắng" if is_white_move else "Đen"

            return f"Lượt {move_number}: {color_turn} đi {last_move_san} ({last_move_uci})"
        except Exception as e:
            return f"Lỗi log nước đi: {e}"

# Hàm tiện ích để kiểm tra nhanh
def test_board_manager():
    """Kiểm tra nhanh ChessBoardManager"""
    print("=== KIỂM TRA CHESS BOARD MANAGER ===")

    # Test 1: Khởi tạo bình thường
    print("\n1. Khởi tạo board mới:")
    manager = ChessBoardManager()
    print(f"   Board type: {type(manager.board)}")
    print(f"   Has piece_at: {hasattr(manager.board, 'piece_at')}")
    print(f"   FEN: {manager.get_fen()}")

    # Test 2: Thực hiện nước đi
    print("\n2. Thực hiện nước đi e2e4:")
    success = manager.make_move("e2e4")
    print(f"   Success: {success}")
    print(f"   Current FEN: {manager.get_fen()}")

    # Test 3: Kiểm tra piece_at
    print("\n3. Kiểm tra piece_at tại e4:")
    piece = manager.get_piece_at("e4")
    print(f"   Piece at e4: {piece}")

    # Test 4: Kiểm tra legal moves
    print("\n4. Kiểm tra legal moves:")
    legal_moves = manager.get_legal_moves()
    print(f"   Số nước đi hợp lệ: {len(legal_moves)}")
    if legal_moves:
        print(f"   Ví dụ: {legal_moves[0]}")

    # Test 5: Reset board
    print("\n5. Reset board:")
    manager.reset_board()
    print(f"   FEN sau reset: {manager.get_fen()}")

    print("\n=== KẾT THÚC KIỂM TRA ===")
    return True


if __name__ == "__main__":
    # Chạy test nếu file được chạy trực tiếp
    test_board_manager()