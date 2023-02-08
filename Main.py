import random
import chess
import chess.polyglot
import time
import sys
import os

pawn_score = [
    0, 0, 0, 0, 0, 0, 0, 0,
    5, 10, 10, -20, -20, 10, 10, 5,
    5, -5, -10, 0, 0, -10, -5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, 5, 10, 25, 25, 10, 5, 5,
    10, 10, 20, 30, 30, 20, 10, 10,
    50, 50, 50, 50, 50, 50, 50, 50,
    0, 0, 0, 0, 0, 0, 0, 0]

knight_score = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50]

bishop_score = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20]

rook_score = [
    0, 0, 0, 5, 5, 0, 0, 0,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    5, 10, 10, 10, 10, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0]

queen_score = [
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 5, 5, 5, 5, 5, 0, -10,
    0, 0, 5, 5, 5, 5, 0, -5,
    -5, 0, 5, 5, 5, 5, 0, -5,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20]

king_score = [
    20, 30, 10, 0, 0, 10, 30, 20,
    20, 20, 0, 0, 0, 0, 20, 20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30]

moves = 1

playing_side = None

board = chess.Board()

piece_dict = {
    'P': 10,
    'N': 30,
    'B': 35,
    'R': 50,
    'Q': 90,
    'K': 1000
}

total_evaluated = 0

total_transpositions = 0

zobrist_table = [[random.getrandbits(64) for _ in range(12)] for _ in range(65)]

transposition_table = {}

unicode_ascii_switch = True

def print_board_with_unicode(board):
    piece_map = {
        chess.PAWN: "♟♙",
        chess.KNIGHT: "♞♘",
        chess.BISHOP: "♝♗",
        chess.ROOK: "♜♖",
        chess.QUEEN: "♛♕",
        chess.KING: "♚♔"
    }
    ascii_map = {
        chess.PAWN: "Pp",
        chess.KNIGHT: "Nn",
        chess.BISHOP: "Bb",
        chess.ROOK: "Rr",
        chess.QUEEN: "Qq",
        chess.KING: "Kk"
    }
    for i in range(8):
        row = ""
        for j in range(8):
            square = chess.square(j, 7 - i)
            if piece := board.piece_at(square):
                if piece.color == chess.WHITE:
                    row += f'{piece_map[piece.piece_type][0]} ' if unicode_ascii_switch else f'{ascii_map[piece.piece_type][0]} '
                else:
                    row += f'{piece_map[piece.piece_type][1]} ' if unicode_ascii_switch else f'{ascii_map[piece.piece_type][1]} '
            else:
                row += "░ " if (i+j) % 2 != 0 else "▓ "
        print(row)

def king_safety(board, side, endgame_weight):  # sourcery skip: sum-comprehension
    king_square = board.king(chess.WHITE) if side else board.king(chess.BLACK)
    danger = 0
    for square in chess.SQUARES:
        if chess.square_distance(king_square, square) == 1 and board.is_attacked_by(not side, square):
            danger += 1
    return max(0, (danger - min(8, endgame_weight)))

def king_forcefulness(board, side, endgame_weight):
    king_square = board.king(chess.BLACK) if side else board.king(chess.WHITE)
    return chess.square_distance(king_square, chess.E5) * (endgame_weight / 3)

def calculate_endgame_weight(board):
    weight = 0
    for square in chess.SQUARES:
        if piece := board.piece_at(square) is not None:
            weight += (piece_dict[piece.symbol().upper()])
    weight /= (moves/5)
    return weight

def central_control_difference(board):
    # define the 4 central squares
    central_squares = (chess.D4, chess.D5, chess.E4, chess.E5)

    # count the number of pieces attacking the central squares for our side
    our_attackers = sum(len(board.attackers(board.turn, square)) for square in central_squares)

    # count the number of pieces attacking the central squares for the opponent's side
    opp_attackers = sum(len(board.attackers(not board.turn, square)) for square in central_squares)

    return our_attackers - opp_attackers

def material_difference(board):
    white_material = 0
    black_material = 0
    to_move = 1 if board.turn == True else -1
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            if piece.symbol() != piece.symbol().upper():
                black_material += piece_dict[piece.symbol().upper()]
            else:
                white_material += piece_dict[piece.symbol().upper()]
    return (white_material - black_material) * to_move * 25

def piece_activation(board):
    # Create empty dictionaries to store the counts for each player
    white_control = {}
    black_control = {}
    # Iterate over all squares on the board
    for square in chess.SQUARES:
        to_move = 1 if board.turn == True else -1
        if piece := board.piece_at(square):
            if piece.color == chess.WHITE:
                if piece.piece_type not in white_control:
                    white_control[piece.piece_type] = 0
                white_control[piece.piece_type] += len(list(board.attacks(square)))
            elif piece.color == chess.BLACK:
                if piece.piece_type not in black_control:
                    black_control[piece.piece_type] = 0
                black_control[piece.piece_type] += len(list(board.attacks(square)))
    # Calculate the difference in square control
    white_total = sum(white_control.values())
    black_total = sum(black_control.values())
    square_diff = white_total - black_total
    return square_diff * to_move

def piece_positions(board, endgame_weight):
    pawns = board.pieces(chess.PAWN, chess.WHITE)
    knights = board.pieces(chess.KNIGHT, chess.WHITE)
    bishops = board.pieces(chess.BISHOP, chess.WHITE)
    rooks = board.pieces(chess.ROOK, chess.WHITE)
    queens = board.pieces(chess.QUEEN, chess.WHITE)
    kings = board.pieces(chess.KING, chess.WHITE)

    score = sum(pawn_score[p] for p in pawns)
    score += sum(knight_score[p] for p in knights)
    score += sum(bishop_score[p] for p in bishops)
    score += sum(rook_score[p] for p in rooks)
    score += sum(queen_score[p] for p in queens)
    score += sum(king_score[p] for p in kings)

    return (1.5 * score) / (endgame_weight + 1)

def endgame_weight(board):
    weight = 0
    for square in chess.SQUARES:
        if piece := board.piece_at(square):
            if piece.symbol().upper() != 'K':
                weight += (piece_dict[piece.symbol().upper()] / 5)
    # 16 is the material for both sides using our piece_dict values divided by 5 excluding Kings
    return 16 - weight

def zobrist_hash(board):
    hash_val = 0
    for square in chess.SQUARES:
        if piece := board.piece_at(square):
            hash_val ^= zobrist_table[square][piece.piece_type - 1]
    if board.turn:
        hash_val ^= zobrist_table[64][0]
    if board.has_kingside_castling_rights(chess.WHITE):
        hash_val ^= zobrist_table[64][1]
    if board.has_queenside_castling_rights(chess.WHITE):
        hash_val ^= zobrist_table[64][2]
    if board.has_kingside_castling_rights(chess.BLACK):
        hash_val ^= zobrist_table[64][3]
    if board.has_queenside_castling_rights(chess.BLACK):
        hash_val ^= zobrist_table[64][4]
    if board.ep_square:
        hash_val ^= zobrist_table[64][5 + chess.square_rank(board.ep_square)]
    return hash_val

def negamax(board, depth, alpha, beta, best_move=None):
    hash_val = zobrist_hash(board)
    if depth == 0:
        return evaluate_position(board, best_move)
    if hash_val in transposition_table:
        stored_depth, stored_val, stored_move = transposition_table[hash_val]
        if stored_depth >= depth:
            global total_transpositions
            total_transpositions += 1
            return stored_val, stored_move
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            score = 1000000
        else:
            score, _ = negamax(board, depth-1, -beta, -alpha, move)
            score = -score
        global total_evaluated
        total_evaluated += 1
        board.pop()
        if score >= beta:
            return score, move
        if score > alpha:
            alpha = score
            best_move = move
    transposition_table[hash_val] = depth, alpha, best_move
    return alpha, best_move


def evaluate_position(board, best_move):
    # TODO: add endgame checkmating algorithm
    weight = endgame_weight(board)
    score = material_difference(board)
    score += piece_activation(board)
    score += central_control_difference(board)
    score += piece_positions(board, weight)
    score += king_forcefulness(board, board.turn, weight)
    score -= king_safety(board, board.turn, weight)
    if board.is_checkmate():
        score += 1000000
    return score, best_move

def attempt_push_move(board):
    move = input("Say 'resign' to resign.\nSay 'switch' to switch between letters and unicode characters.\nEnter your move in SAN notation:\n")
    if str(move) == "switch":
        global unicode_ascii_switch
        unicode_ascii_switch = not unicode_ascii_switch
        os.system('cls' if os.name == 'nt' else 'clear')
        print_board_with_unicode(board)
        attempt_push_move(board)
    elif str(move) == "resign":
        sys.exit('Player resigns. AI wins!')
    else:
        try:
            board.push(board.parse_san(move))
            if board.is_checkmate():
                sys.exit(f"Player checkmated AI after {moves} move(s)!")
            os.system('cls' if os.name == 'nt' else 'clear')
            print_board_with_unicode(board)
        except Exception:
            print("Illegal move. Try again.")
            attempt_push_move(board)

total_evaluated = 0
while not board.is_game_over():
    os.system('cls' if os.name == 'nt' else 'clear')
    playing_side = board.turn
    ai_move = ''
    with chess.polyglot.open_reader("Titans.bin") as reader:
        if entries := list(reader.find_all(board)):
            first_n_entries = entries[:4]
            ai_move = random.choice(first_n_entries).move
        else:
            start = time.perf_counter()
            _, ai_move = negamax(board, 4, float("-inf"), float("inf"))
            end = time.perf_counter()
            print(f"AI move: {board.san(ai_move)}")
            print(f"Evaluated {total_evaluated} positions in {((end - start)*1000):0.4f} millis for {total_evaluated/(end - start):0.1f} positions per second")
            print(f"Eliminated {total_transpositions} transpositions")
    board.push(ai_move)
    if board.is_checkmate():
        sys.exit(f"AI checkmated player after {moves} move(s)!")
    print_board_with_unicode(board)
    attempt_push_move(board)
    moves += 1