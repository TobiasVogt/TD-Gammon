import itertools
import numpy as np
import random
from libc.stdlib cimport rand

class Game:
    
    PLAYERS = ['black', 'white']

    def __init__(self):
        #Spielbrett. Index ist Position auf dem Spielfeld und der Wert die Anzahl der Steine auf dem Feld
        #Diese Zahl ist positiv für schwarze und negativ für Weiße Steine
        cdef int points[24]
        points[:] = [2,0,0,0,0,-5,0,-3,0,0,0,5,-5,0,0,0,3,0,5,0,0,0,0,-2]
        self.points = points
        #Steinpositionen
        self.refresh_piece_positions()
        #Steine die auf der Bar sind
        self.black_taken = 0
        self.white_taken = 0
        self.players = ['black', 'white']
        self.turns = 0
        
    # Methode die exakt die 198 Features liefert die in TD-Gammon 0.0 benutzt wurden
    # Nach "Reinforcement Learning: An Introduction", Sutton & Barto, 2017
    def extractFeatures(self, player):
        points = self.points
        # 196 Features kodieren den Zustand der Spielfelder, 98 für jeden Spieler
        # 0,1,2,3,4,5 Steine werden kodiert als
        # 0000, 1000, 1100, 1110, 1110.5, 1111
        # (4. Bit = (n-3)/2)
        features = []
        #Weiße Steine codieren
        whites = 0
        for point in points[:24]:
            point = -point
            if point > 0:
                whites += point
                features += self.encodePoint(point)
            else:
                features += [0.,0.,0.,0.]
        #Weiße Steine auf der "Bar", n/2
        features.append(self.white_taken/2.)
        #Weiße Steine die bereits aus dem Spiel sind, n/15
        off = 15 - whites + self.white_taken
        features.append(off/15.)
        #Schwarze Steine codieren
        blacks = 0
        for point in points[:24]:
            if point > 0:
                blacks += point
                features += self.encodePoint(point)
            else:
                features += [0.,0.,0.,0.]
        #Schwarze Steine auf der "Bar", n/2
        features.append(self.black_taken/2.)
        #Schwarze Steine die bereits aus dem Spiel sind, n/15
        off = 15 - blacks + self.black_taken
        features.append(off/15.)
        # Zwei Features für den derzeitigen Spieler
        if player == self.players[0]:
            features += [1., 0.]
        else:
            features += [0., 1.]
        return np.array(features).reshape(1, -1)
    
    def encodePoint(self, point):
        if point == 0:
            return [0.,0.,0.,0.]
        elif point == 1:
            return [1.,0.,0.,0.]
        elif point == 2:
            return [1.,1.,0.,0.]
        elif point == 3:
            return [1.,1.,1.,0.]
        else:
            return [1.,1.,1.,(point-3)/2.]
        
    def play(self, player, debug=False):
        cdef int player_num
        #Wer anfängt ist zufällig
        player_num = rand() % 2
        #Solange spielen bis es einen Gewinner gibt
        while not self.get_winner():
            #Zug ausführen
            self.next_step(player[player_num], player_num, debug=debug)
            #Der andere Spieler ist dran
            player_num = (player_num + 1) % 2
        #Siegesstats ausgeben
        #self.print_game_state()
        return self.get_winner()

    def play_random_fast(self, start_player, debug=False):
        player_num = 0 if start_player == self.players[0] else 1
        while not self.get_winner():
            #Zug ausführen (zwei Zufallswürfel)
            move1 = self.execute_random_move(self.players[player_num])
            move2 = self.execute_random_move(self.players[player_num])
            #Der andere Spieler ist dran
            player_num = (player_num + 1) % 2
            #Debuggen
            if debug:
                print("Current Player:", self.players[player_num])
                print("Move:", move1, move2)
                self.print_game_state()
                print()
        return self.get_winner()
        
    def execute_random_move(self, player):
        chk = self.black_checkers[:] if player == self.players[0] else self.white_checkers[:]
        random.shuffle(chk)
        dice = random.randint(1,6)
        if player == self.players[1]:
            dice = -dice
        #Steine auf der Bar
        if player == self.players[0] and self.black_taken > 0 or player == self.players[1] and self.white_taken > 0:
            pos = dice - 1 if player == self.players[0] else len(self.points) + dice
            if self.is_target_valid(pos, player):
                self.execute_move(('bar', pos), player)
                return ('bar', pos)
        else:
            #Steine auf dem Brett
            for c in chk:
                if self.is_target_valid(c + dice, player):
                    self.execute_move((c, c + dice), player)
                    return (c, c + dice)
    
    def next_step(self, player, player_num, debug=False):
        cdef int a,b
        self.turns += 1
        #Würfeln
        a = rand() % 6 + 1
        b = rand() % 6 + 1
        roll = (a, b)
        #Züge berechnen
        moves = self.get_moves(roll, self.players[player_num])
        #Spieler fragen welche der Züge er gerne ausführen möchte
        move = player.get_action(moves, self) if moves else None
        #Zug ausführen falls es möglich ist 
        if move:
            #Einzelne Unterzüge ausführen
            if debug:
                print(move)
            self.execute_moves(move, self.players[player_num])
        #Debuggen
        if debug:
            print("Current Player:", self.players[player_num])
            print("Moves:", moves)
            print("Roll:", roll, "| Move:", move)
            self.print_game_state()
            print()
            
    def execute_moves(self, moves, player):
        #Unterzüge ausführen
        for m in moves:
            self.execute_move(m, player)
            
    #Führt einen Zug aus und gibt die vorherige Spielposition zurück
    def execute_move(self, move, player):
        if move != (0,0):
            piece = 1 if player == self.players[0] else - 1
            #Stein von der alten Position nehmen, falls nicht auf der Bar
            if move[0] != "bar":
                self.points[move[0]] -= piece
            elif player == self.players[0]:
                self.black_taken -= 1
            else:
                self.white_taken -= 1
            #Stein auf die gewünschte Stelle setzen, falls noch auf dem Spielfeld
            if move[1] >= 0 and move[1] < len(self.points):
                #Falls dort bereits ein Gegnerstein war wird er auf die Bar gelegt
                if player == self.players[0] and self.points[move[1]] == -1:
                    self.points[move[1]] = 0
                    self.white_taken += 1
                elif player == self.players[1] and self.points[move[1]] == 1:
                    self.points[move[1]] = 0
                    self.black_taken += 1
                #Stein platzieren
                self.points[move[1]] += piece
            #Positionen der schwarzen und weißen Steine aktualisieren
            self.refresh_piece_positions()

    def get_state(self):
        return (self.points[:], self.black_taken, self.white_taken)

    #Setzt das Spiel auf die gegebene Spielposition (zurück)
    def reset_to_state(self, state):
        self.points = state[0][:]
        self.black_taken = state[1]
        self.white_taken = state[2]
        #Positionen der schwarzen und weißen Steine aktualisieren
        self.refresh_piece_positions()

    #Aktualisiert die Listen mit den Position der Steine
    def refresh_piece_positions(self):
        #Positionen der schwarzen Steine
        self.black_checkers = [i for i in range(24) if self.points[i] > 0]
        #Positionen der weißen Steine
        self.white_checkers = sorted([i for i in range(24) if self.points[i] < 0], reverse=True)
    
    def get_moves(self, roll, player):
        #Pasch?
        if roll[0] == roll[1]:
            return self.get_quad_moves(roll[0], player)
        #Hat der Spieler Steine die er erst wieder ins Spiel bringen muss?
        if self.has_bar_pieces(player):
            return self.get_bar_to_board_moves(roll, player)
        #Sonstige Züge finden
        else:
            return self.generate_moves(roll, player)

    def get_bar_to_board_moves(self, roll, player):
        moves = []
        #Sind die Heimfelder blockiert die die Würfel anzeigen?
        pos0 = roll[0] - 1 if player == self.players[0] else len(self.points) - roll[0]
        pos1 = roll[1] - 1 if player == self.players[0] else len(self.points) - roll[1]
        val1 = self.is_target_valid(pos0, player)
        val2 = self.is_target_valid(pos1, player)
        taken = self.black_taken if player == self.players[0] else self.white_taken
        #Falls beide Würfel genutzt werden können müssen sie genutzt werden
        if taken > 1 and val1 and val2:
            moves.append((("bar", pos0), ("bar", pos1)))
        else:
            #Falls nicht möglich, andere Züge für den zweiten würfel finden
            if val1:
                bar_move = ("bar", pos0)
                singles = self.generate_single_move(bar_move, roll[1], player)
                moves += [(bar_move, s) for s in singles]
            if val2:
                bar_move = ("bar", pos1)
                singles = self.generate_single_move(bar_move, roll[0], player)
                moves += [(bar_move, s) for s in singles]
        return moves

    def generate_moves(self, roll, player):
        valid = self.is_target_valid
        board = self.points
        #Alle zweier Kombinationen aus den derzeitigen Positionen ermitteln
        chk = self.black_checkers if player == self.players[0] else self.white_checkers
        comb = list(itertools.combinations(chk, 2))
        comb += [(a,a) for a in chk if board[a] > 1 or board[a] < -1]
        #Züge suchen
        moves = []
        #Schwarz geht die Zahlen hoch, Weiß runter
        if player == self.players[1]:
            roll = (-roll[0], -roll[1])
        #Jeden Zug prüfen
        for (a,b) in comb:
            #Zwei Steine Bewegen
            a0 = valid(a + roll[0], player)
            a1 = valid(a + roll[1], player)
            if a0 and valid(b + roll[1], player):
                moves.append(((a, a + roll[0]), (b, b + roll[1])))
            if a1 and valid(b + roll[0], player) and not (a==b and a0):
                moves.append(((a, a + roll[1]), (b, b + roll[0])))
            #Ein Stein bewegen
            farpos = a + roll[0] + roll[1]
            if a == b and farpos >= 0 and farpos < len(self.points) and valid(farpos, player):
                if a0:
                    moves.append(((a, a + roll[0]), (a + roll[0], farpos)))
                elif a1:
                    moves.append(((a, a + roll[1]), (a + roll[1], farpos)))
        #Falls man keine zwei Züge generieren kann, schauen ob man vielleicht einen Einzelnen schafft
        if moves == []:
            m1 = self.generate_single_move(prev_move=None, dice=roll[0], player=player)
            m2 = self.generate_single_move(prev_move=None, dice=roll[1], player=player)
            m1.extend(m2)
            moves += [((0,0), m) for m in m1]
        #Zurückgeben
        return moves
    
    def generate_single_move(self, prev_move, dice, player):
        chk = self.black_checkers if player == self.players[0] else self.white_checkers
        if player == self.players[1] and dice > 0:
            dice = -dice
        #Alle normalen Züge 
        moves = [(x, x + dice) for x in chk if self.is_target_valid(x + dice, player)]
        #kann man den Stein direkt weiter ziehen?
        if prev_move and self.is_target_valid(prev_move[1] + dice, player):
            moves.append((prev_move[1], prev_move[1] + dice))
        return moves
    
    def generate_double_move(self, prev_move, dice, player):
        chk = self.black_checkers if player == self.players[0] else self.white_checkers
        if player == self.players[1] and dice > 0:
            dice = -dice
        #Einzelzüge besorgen
        s_moves = self.generate_single_move(prev_move, dice, player)
        #Weiteren Zug anhängen
        moves = [((a,b),(b,b+dice)) for (a,b) in s_moves if self.is_target_valid(b+dice, player)]
        for x in chk:
            for y in s_moves:
                if self.is_target_valid(x+dice, player):
                    if ((x,x+dice) == y and self.points[x] > 2) or (x,x+dice) != y:
                        moves.append((y, (x,x+dice)))
        return moves
            
    def generate_triple_move(self, prev_move, dice, player):
        chk = self.black_checkers if player == self.players[0] else self.white_checkers
        if player == self.players[1] and dice > 0:
            dice = -dice
        #Doppelzüge besorgen
        d_moves = self.generate_double_move(prev_move, dice, player)
        #Weiteren Zug anhängen
        moves = [((a,b), (c,d), (d, d+dice)) for ((a,b), (c,d)) in d_moves if self.is_target_valid(d+dice, player)]
        for x in chk:
            for (y,z) in d_moves:
                if self.is_target_valid(x+dice, player):
                    if (((x,x+dice) == y or (x,x+dice) == z) and self.points[x] > 2) or ((x,x+dice) != y and (x,x+dice) != z):
                        moves.append((y, z, (x,x+dice)))
        return moves
            
    #Bei einem Pasch müssen 4 Züge ausgeführt werden
    def get_quad_moves(self, dice, player):
        #Bis zu 4 Steine von der Bar bewegen
        if self.has_bar_pieces(player):
            return self.get_quad_bar_to_board_moves(dice, player)
        #4 Züge finden
        else:
            return self.generate_quad_moves(dice, player)
        
    def get_quad_bar_to_board_moves(self, dice, player):
        moves = []
        #Ist das von den Würfeln gezeigt Heimfeld blockiert?
        pos = dice - 1 if player == self.players[0] else len(self.points) - dice
        valid = self.is_target_valid(pos, player)
        taken = self.black_taken if player == self.players[0] else self.white_taken
        #Falls alle Würfel genutzt werden können müssen sie genutzt werden
        if valid:
            bar_move = ("bar", pos)
            if taken >= 4:
                moves.append((bar_move, bar_move, bar_move, bar_move))
            elif taken == 3:
                singles = self.generate_single_move(bar_move, dice, player)
                moves += [(bar_move, bar_move, bar_move, s) for s in singles]
            elif taken == 2:
                doubles = self.generate_double_move(bar_move, dice, player)
                moves += [(bar_move, bar_move, d1, d2) for (d1, d2) in doubles]
            else:
                triples = self.generate_triple_move(bar_move, dice, player)
                moves += [(bar_move, t1, t2, t3) for (t1, t2, t3) in triples]
        return moves
  
    """
        Kombinationsmöglichkeiten:
        1. quad
        2. triple + single
        3. double + double
        4. double + single + single
        5. single + single + single + single
        
        Der Genickbruch eines jeden schnellen Backgammon-Programms:
        Die Berechnung von allen Möglichkeiten bei 4 Würfeln!
    """
    def generate_quad_moves(self, dice, player):
        #Optimieren
        board = self.points
        valid = self.is_target_valid
        #Weiß läuft entgengesetzt
        if player == self.players[1] and dice > 0:
            dice = -dice
        #Alle zweier Kombinationen aus den derzeitigen Positionen ermitteln
        chk = self.black_checkers if player == self.players[0] else self.white_checkers
        #Alle Positionen mit mindestens einem Stein
        single = chk[:]
        #Alle Positionen mit mindestens zwei Steinen
        double = [x for x in chk if abs(board[x]) >= 2]
        #Alle Positionen mit mindestens drei Steinen
        triple = [x for x in chk if abs(board[x]) >= 3]
        #Alle Positionen mit mindestens vier Steinen
        quad = [x for x in chk if abs(board[x]) >= 4]
        #Gültige Zielpunkte sammeln
        valid_dict = {}
        for s in single:
            for i in range(4):
                target = s+dice*(i+1)
                if target not in valid_dict:
                    if i == 0:
                        valid_dict[target] = valid(target, player)
                    else:
                        valid_dict[target] = valid(target, player) and target >= 0 and target < len(self.points)
                        
        moves = []
        
        #Quads, 1. Kombination
        for q in quad:
            if valid_dict[q+dice]:
                moves.append(((q, q+dice),(q, q+dice),(q, q+dice),(q, q+dice)))
                
        #Triples
        for t in triple:
            #2. Kombination
            for s in single:
                if t != s and valid_dict[t+dice] and valid_dict[s+dice]:
                    moves.append(((t, t+dice),(t, t+dice),(t, t+dice),(s, s+dice)))
            #Folgezüge für triples
            if valid_dict[t+dice] and valid_dict[t+dice*2]:
                moves.append(((t, t+dice),(t, t+dice),(t, t+dice),(t+dice, t+dice*2)))   
                
        #Doubles
        for d in double:
            d1 = valid_dict[d+dice]
            d2 = valid_dict[d+dice*2]
            d3 = valid_dict[d+dice*3]
            #3. Kombination
            for ds in double:
                #Keine Doppelten bitte
                if ds > d:
                    if d1 and valid_dict[ds+dice]:
                        moves.append(((d, d+dice),(d, d+dice),(ds, ds+dice),(ds, ds+dice)))
            #4. Kombination
            for s1 in single:
                for s2 in single:
                    if s2 > s1 and d != s1 and d != s2:
                        if valid_dict[d+dice] and valid_dict[s1+dice] and valid_dict[s2+dice]:
                            moves.append(((d, d+dice),(d, d+dice),(s1, s1+dice),(s2, s2+dice)))
                #Doppelzug gefolgt von einem Folgezug und einem single
                if d1 and d2 and d != s1 and valid_dict[s1+dice]:
                        moves.append(((d, d+dice),(d, d+dice),(d+dice, d+dice*2),(s1, s1+dice)))
            #Folgezüge für doubles
            #Jeweils zwei Züge mit zwei Steinen
            if d1 and d2:
                moves.append(((d, d+dice),(d, d+dice),(d+dice, d+dice*2),(d+dice, d+dice*2)))
            #Ein double gefolgt von einem doppelten Folgezug
            if d1 and d2 and d3:
                moves.append(((d, d+dice),(d, d+dice),(d+dice, d+dice*2),(d+dice*2, d+dice*3)))

        #Singles
        for s1 in single:
            sv1 = valid_dict[s1+dice]
            sv2 = valid_dict[s1+dice*2]
            sv3 = valid_dict[s1+dice*3]
            sv4 = valid_dict[s1+dice*4]
            for s2 in single:
                sec1 = valid_dict[s2+dice]
                sec2 = valid_dict[s2+dice*2]
                sec3 = valid_dict[s2+dice*3]
                for s3 in single:
                    for s4 in single:
                        #5. Kombination
                        if s4 > s3 > s2 > s1:
                            if sv1 and valid_dict[s2+dice] and valid_dict[s3+dice] and valid_dict[s4+dice]:
                                moves.append(((s1, s1+dice),(s2, s2+dice),(s3, s3+dice),(s4, s4+dice)))
                    #Züge mit mindestens drei Steinen
                    if s2 > s1 and s3 != s2 and s3 != s1:
                        #Zwei Einzelzüge gefolgt von einem Folgezug
                        if sv1 and sec1 and valid_dict[s3+dice] and valid_dict[s3+dice*2]:
                            moves.append(((s1, s1+dice),(s2, s2+dice),(s3, s3+dice),(s3+dice, s3+dice*2)))
                
            #Folgezüge für singles
                if s2 > s1:
                    #Ein Zug mit dem ersten Stein und drei mit dem zweiten
                    if sv1 and sec1 and sec2 and sec3:
                        moves.append(((s1, s1+dice),(s2, s2+dice),(s2+dice, s2+dice*2),(s2+dice*2, s2+dice*3)))
                    #Zwei Züge mit dem ersten und zwei mit dem zweiten
                    if sv1 and sv2 and sec1 and sec2:
                        moves.append(((s1, s1+dice),(s1+dice, s1+dice*2),(s2, s2+dice),(s2+dice, s2+dice*2)))
                    #Drei Züge mit dem ersten Stein und einen weiteren mit dem zweiten
                    if sv1 and sv2 and sv3 and sec1:
                        moves.append(((s1, s1+dice),(s1+dice, s1+dice*2),(s1+dice*2, s1+dice*3),(s2, s2+dice)))
            #Zwei Züge mit dem ersten Stein gefolgt von einem double
            for d in double:
                if d != s1 and sv1 and sv2 and valid_dict[d+dice]:
                    moves.append(((s1, s1+dice),(s1+dice, s1+dice*2),(d, d+dice),(d, d+dice)))
                    
            #Vier Züge mit einem einzigen Stein
            if sv1 and sv2 and sv3 and sv4:
                moves.append(((s1, s1+dice),(s1+dice, s1+dice*2),(s1+dice*2, s1+dice*3),(s1+dice*3, s1+dice*4)))

        #Tupel sortieren um Doppelte zu finden und zu löschen
        #Erhöht zwar hier den Rechenaufwand, aber reduziert die Anzahl der Züge erheblich!
        if player == self.players[0]:
            return set([tuple(sorted(x)) for x in moves])
        else:
            return set([tuple(sorted(x, reverse=True)) for x in moves])

   #Prüft ob das angegeben Ziel gültig ist
    def is_target_valid(self, int target, str player):
        #Landen wir jenseis des Spielbretts?
        if target < 0 or target >= len(self.points):
            return self.can_offboard(player)
        #Prüfen ob das Ziel blockiert ist (2 oder mehr Gegnersteine vorhanden)
        if player == self.players[0]:
            return self.points[target] > -2
        elif player == self.players[1]:
            return self.points[target] < 2
            
    #Hat der Spieler Steine die vom Gegner rausgeworfen wurden?
    def has_bar_pieces(self, str player):
        if player == self.players[0]:
            return self.black_taken > 0
        elif player == self.players[1]:
            return self.white_taken > 0
    
    #Hat der Spieler alle seine Steine in seiner Homezone?
    def can_offboard(self, str player):
        if player == self.players[0]:
            return self.black_taken == 0 and self.black_checkers[0] > 18
        elif player == self.players[1]:
            return self.white_taken == 0 and self.white_checkers[0] < 7
        
    #Gibt den Gewinner zurück falls es einen gibt
    def get_winner(self):
        if self.black_checkers == [] and self.black_taken == 0:
            return self.players[0]
        elif self.white_checkers == [] and self.white_taken == 0:
            return self.players[1]
        else:
            return None
        
    def get_opponent(self, player):
        return self.players[0] if player == self.players[1] else self.players[1]
    
    def Clone(self):
        g = Game()
        g.reset_to_state(self.get_state())
        return g

    def print_game_state(self):
        print("GameState:", self.points, "|", self.black_checkers, "|", self.white_checkers)
        bl = sum([self.points[i] for i in range(len(self.points)) if self.points[i] > 0])
        wt = sum([self.points[i] for i in range(len(self.points)) if self.points[i] < 0])
        print("Black/White:", bl, "/", wt, "Bar:", self.black_taken, "/", self.white_taken)