from abc import ABC, abstractmethod
import random
import math


# Von ABC erben = Abstrakte Klasse
class Player(ABC):
    
    # In der init-Methode erhält der Spieler den Spieler den er im Spiel repräsentiert: 
    # Schwarz/Weiß, black/white, x/o o.ä.
    def __init__(self, player):
        self.player = player
        
    # Wähle einen Zug aus actions und gib ihn zurück
    @abstractmethod
    def get_action(self, actions, game):
        pass
    
    # Teile uns deinen Namen mit, Spieler!
    @abstractmethod
    def get_name(self):
        pass
		
class RandomPlayer(Player):
    
    def get_action(self, actions, game):
        return random.choice(list(actions)) if actions else None
    
    def get_name(self):
        return "RandomPlayer"
		
		
"""

ValuePlayer und mögliche Implementationen von Value-Funktionen

"""		

class ValuePlayer(Player):
    
    def __init__(self, player, valuefunction):
        Player.__init__(self, player)
        self.value = valuefunction
        
    def get_action(self, actions, game):
        # Spielstatus speichern
        old_state = game.get_state()
        # Variablen initialisieren
        best_value = float("-inf")
        best_action = None
        # Alle Züge durchsuchen
        for a in actions:
            # Zug ausführen
            game.execute_moves(a, self.player)
            # Spielstatus bewerten
            value = self.value(game, self.player)
            # Besten merken
            if value > best_value:
                best_value = value
                best_action = a
            # Spiel zurücksetzen
            game.reset_to_state(old_state)
        return best_action
    
    def get_name(self):
        return "ValuePlayer [" + self.value.__name__ + "]"
		
def way_to_go(game, player):
    # Seite ermitteln
    black = player == game.players[0]
    # Steine besorgen
    enemy_checkers = game.white_checkers if black else game.black_checkers
    # Schritte berechnen
    steps = 0
    # Steine auf dem Spielfeld
    for tower in enemy_checkers:
        if black:
            steps += (24 - tower) * game.points[tower]
        else:
            steps += tower * game.points[tower] * -1
    # Steine auf der Bar
    bar_chk = game.white_taken if black else game.black_taken
    steps += 25 * bar_chk 
    return steps / 375
	
def singleton(game, player):
    chk = game.black_checkers if player == game.players[0] else game.white_checkers
    singles = 0
    for i in chk:
        if abs(game.points[i]) == 1:
            singles += 1
            
    # Zahl in [0,1]
    return (15 - singles) / 15
	
def single_to_go(game, player):
    return singleton(game, player) + way_to_go(game, player)
	
def blocker(game, player):
    chk = game.black_checkers if player == game.players[0] else game.white_checkers
    blocked = len([x for x in chk if abs(game.points[x]) >= 2])
    return blocked / 7
	
"""
ModelPlayer
"""

class ModelPlayer(ValuePlayer):
    
    def __init__(self, player, model):
        ValuePlayer.__init__(self, player, self.get_value)
        self.model = model
        
    def get_value(self, game, player):
        features = game.extractFeatures(player)
        v = self.model.get_output(features)
        v = 1 - v if self.player == game.players[0] else v
        return v
    
    def get_name(self):
        return "ModelPlayer [" + self.model.get_name() +"]"
		
"""
2-ply
"""
		
class TwoPlyValuePlayer(ValuePlayer):
    
    def get_action(self, actions, game):
        # Spielstatus speichern
        old_state = game.get_state()
        # Variablen initialisieren
        best_value = float("-inf")
        best_action = None
        # Alle Züge durchsuchen
        for a in actions:
            # Zug ausführen
            game.execute_moves(a, self.player)
            # Spielstatus bewerten
            value = self.two_ply(game, self.player)
            # Besten merken
            if value > best_value:
                best_value = value
                best_action = a
            # Spiel zurücksetzen
            game.reset_to_state(old_state)
        return best_action
        
    def two_ply(self, game, player):
        # Alle möglichen Gegnerwürfe und dazugehörige Züge bewerten und mit der WS des Wurfes multiplizieren
        all_rolls = [(a,b) for a in range(1,7) for b in range(a,7)]
        value = 0
        for roll in all_rolls:
            probability = 1/18 if roll[0] != roll[1] else 1/36
            state = game.get_state()
            moves = game.get_moves(roll, game.get_opponent(player))
            min_val = 1
            for move in moves:
                game.execute_moves(move, game.get_opponent(player))
                v = self.value(game, player)
                game.reset_to_state(state)
                if v < min_val:
                    min_val = v
            value += probability * min_val
        # Wert zurückgeben
        return value

    def get_name(self):
        return "TwoPlyValuePlayer [" + self.value.__name__ + "]"

class TwoPlyModelPlayer(TwoPlyValuePlayer):

    def __init__(self, player, model):
        TwoPlyValuePlayer.__init__(self, player, self.get_value)
        self.model = model
        
    def get_value(self, game, player):
        features = game.extractFeatures(player)
        v = self.model.get_output(features)
        v = 1 - v if self.player == game.players[0] else v
        return v
    
    def get_name(self):
        return "TwoPlyModelPlayer [" + self.model.get_name() +"]"
		
"""
3-ply
"""

class ThreePlyValuePlayer(TwoPlyValuePlayer):
    
    # Die Methode aus dem TwoPlyValuePlayer, nur die Value Funktion ist gegen 3-ply ausgetauscht
    def two_ply(self, game, player):
        # Alle möglichen Gegnerwürfe und dazugehörige Züge bewerten und mit der WS des Wurfes multiplizieren
        all_rolls = [(a,b) for a in range(1,7) for b in range(a,7)]
        value = 0
        for roll in all_rolls:
            probability = 1/18 if roll[0] != roll[1] else 1/36
            state = game.get_state()
            # Wir betrachten die Gegnerzüge
            moves = game.get_moves(roll, game.get_opponent(player))
            min_val = 1
            for move in moves:
                game.execute_moves(move, game.get_opponent(player))
                # Bewertet wird aber aus unserer Perspektive
                v = self.three_ply(game, player)
                if v < min_val:
                    min_val = v
                game.reset_to_state(state)
            value += probability * min_val
        # Wert zurückgeben
        return value
    
    # Wie two_ply nur das diesmal maximiert wird
    def three_ply(self, game, player):
        # Alle möglichen Würfe und dazugehörige Züge bewerten und mit der WS des Wurfes multiplizieren
        all_rolls = [(a,b) for a in range(1,7) for b in range(a,7)]
        value = 0
        for roll in all_rolls:
            probability = 1/18 if roll[0] != roll[1] else 1/36
            state = game.get_state()
            moves = game.get_moves(roll, player)
            max_val = 0
            for move in moves:
                game.execute_moves(move, player)
                # Bewertet wird aber aus unserer Perspektive
                v = self.value(game, player)
                if v > max_val:
                    max_val = v
                game.reset_to_state(state)
            value += probability * max_val
        # Wert zurückgeben
        return value
    
    def get_name(self):
        return "ThreePlyValuePlayer [" + self.value.__name__ + "]"
		
		
"""
Expectiminimax
"""

class ExpectiminimaxValuePlayer(ValuePlayer):

    # Konstruktor braucht einen Parameter für die maximal Suchtiefe
    # 0 = 1-ply, 1= 2-ply, 2 = 3-ply, usw.
    def __init__(self, player, valuefunction, max_depth):
        ValuePlayer.__init__(self, player, valuefunction)
        self.max_depth = max_depth
    
    def get_action(self, actions, game):
        # Spielstatus speichern
        old_state = game.get_state()
        # Variablen initialisieren
        best_value = -1
        best_action = None
        # Alle Züge durchsuchen
        for a in actions:
            # Zug ausführen
            game.execute_moves(a, self.player)
            # Spielstatus bewerten
            value = self.expectiminimax(game, 0)
            # Besten merken
            if value > best_value:
                best_value = value
                best_action = a
            # Spiel zurücksetzen
            game.reset_to_state(old_state)
        return best_action
        
    def expectiminimax(self, game, depth):
        # Blatt in unserem Baum
        if depth == self.max_depth:
            return self.value(game, self.player)
        else:
            # Alle möglichen Würfe betrachten
            all_rolls = [(a,b) for a in range(1,7) for b in range(a,7)]
            value = 0
            for roll in all_rolls:
                # Wahrscheinlichkeiten von jedem Wurf
                probability = 1/18 if roll[0] != roll[1] else 1/36
                state = game.get_state()
                # Min-Knoten
                if depth % 2 == 0:
                    moves = game.get_moves(roll, game.get_opponent(self.player))
                    temp_val = 1
                    for move in moves:
                        game.execute_moves(move, game.get_opponent(self.player))
                        # Bewertet wird aber aus unserer Perspektive
                        v = self.expectiminimax(game, depth + 1)
                        if v < temp_val:
                            temp_val = v
                # Max-Knoten
                else:
                    moves = game.get_moves(roll, self.player)
                    temp_val = 0
                    for move in moves:
                        game.execute_moves(move, self.player)
                        # Bewertet wird aber aus unserer Perspektive
                        v = self.expectiminimax(game, depth + 1)
                        if v > temp_val:
                            temp_val = v
                # Spiel zurücksetzen    
                game.reset_to_state(state)
                # Wert gewichtet addieren
                value += probability * temp_val
            return value
    
    def get_name(self):
        return "ExpectiminimaxValuePlayer [" + self.value.__name__ + "]"
    

class ExpectiminimaxModelPlayer(ExpectiminimaxValuePlayer):
    
    def __init__(self, player, model, depth):
        ExpectiminimaxValuePlayer.__init__(self, player, self.get_value, depth)
        self.model = model
        
    def get_value(self, game, player):
        features = game.extractFeatures(player)
        v = self.model.get_output(features)
        v = 1 - v if self.player == game.players[0] else v
        return v
    
    def get_name(self):
        return "EMinMaxModelPlayer [" + self.model.get_name() +"]"
    
class Node:
    
    #Erzeugt einen neuen Knoten
    def __init__(self, move = None, parent = None, actions = None, player = None, value = None):
        self.move = move
        self.parentNode = parent
        self.childNodes = []
        self.wins = 0
        self.visits = 0
        self.untriedMoves = list(actions)
        self.playerJustMoved = player
        self.function_value = value
        
    #Wendet die UCB1 Formel an um den besten Knoten zu finden
    def UCTSelectChild(self):
        s = sorted(self.childNodes, key = lambda c: c.wins/c.visits + math.sqrt(2*math.log(self.visits)/c.visits))[-1]
        return s
    
    #Hängt einen neuen Knoten an den Baum mit diesem Knoten als Vaterknoten
    def AddChild(self, m, a, p, v):
        n = Node(move = m, parent = self, actions = a, player = p, value = v)
        self.untriedMoves.remove(m)
        self.childNodes.append(n)
        return n
    
    #Updated die Statistik
    def Update(self, result):
        self.visits += 1
        self.wins += result
        
    # Berechnet den Wert des Knoten aus dem durschnittlichen Wert der Nachfolger
    def get_value(self):
        val = 0
        for c in self.childNodes:
            val += c.get_value()
        # Keine Nachfolger
        if val == 0:
            return self.function_value
        # Durchschnitt berechnen
        return val / len(self.childNodes)

class MCTSValuePlayer(ValuePlayer):
    
    def get_action(self, actions, game):
        return self.MCTS(actions, game, 5000)

    def MCTS(self, actions, rootgame, itermax):
        #Erstellt die Wurzel
        rootnode = Node(actions = actions, player = self.player)

        #Solange wie man Geduld hat wird ein baum erstellt, erweitert und Spiele zufällig zuende gespielt,
        #um am Ende den am meisten besuchten Knoten zurückzugeben
        for i in range(itermax):
            #Zur Wurzel zurückgehen und das Spiel zurück in den ausgangszustand bringen
            node = rootnode
            game = rootgame.Clone()

            #Phase 1: Selection. Sucht ein geeignetes Blatt mit dem UCB1 Algorithmus
            while node.untriedMoves == [] and node.childNodes != []:
                node = node.UCTSelectChild()
                #Bringt das Spiel in den jeweils zugehörigen Zustand
                game.execute_moves(node.move, game.get_opponent(node.playerJustMoved))

            #Phase 2: Expansion. Hängt den von der value-function als besten Zug bezeichneten Zug an den Baum an
            if node.untriedMoves != []:
                #Value-function fragen was wir denn nehmen sollten!
                #m = ValuePlayer.get_action(self, node.untriedMoves, game) 
                m = random.choice(node.untriedMoves)
                #Daten für neuen Knoten sammeln
                game.execute_moves(m, node.playerJustMoved)
                value = self.value(game, self.player)
                next_player = game.get_opponent(node.playerJustMoved)
                #Einmal Würfeln und Züge besorgen
                next_actions = []
                #roll = (random.randint(1,6), random.randint(1,6))
                rolls = [(i,j) for i in range(1,7) for j in range(i,7)]
                for roll in rolls:
                    next_actions.extend(game.get_moves(roll, next_player))
                #Neuen Knoten erzeugen und anhängen
                node = node.AddChild(m, next_actions, next_player, value)

            #Phase 3: Simulation. Spielt das Spiel von dem gewählten Knoten aus zufällig zuende und ermittelt dem Gewinner
            winner = game.play_random_fast(node.playerJustMoved)
            
            #Phase 4: Backpropagation. Update alle Vorgängerknoten bis hin zu Wurzel und erhöhe ggf. den Siegeszähler
            while node != None:
                #Siegeszähler deren Knoten erhöhen die den Sieger als Spieler eingetragen haben
                result = 1 if winner == node.playerJustMoved else 0
                node.Update(result)
                node = node.parentNode
                
        #Baum Statistik
        #print(rootnode.childNodes, len(rootnode.childNodes), len(actions))
        #Denjenigen Nachfolger von der Wurzel nehmen, der am meisten besucht wurde
        rootchilds = sorted(rootnode.childNodes, key = lambda c: c.get_value())
        best_move = rootchilds[-1].move
        #self.print_tree(rootnode)
        return best_move
    
    def get_value(self, action, game):
        old_state = game.get_state()
        # Zug ausführen
        game.execute_moves(action, self.player)
        # Spielstatus bewerten
        value = self.value(game, self.player)
        # Spiel zurücksetzen
        game.reset_to_state(old_state)
        return value
    
    def print_tree(self, root):
        print(root.move, root.visits, root.wins, root.function_value, root.get_value())
        for c in root.childNodes:
            print("->", c.move, c.visits, c.wins, c.function_value, c.get_value())
    
        
    def get_name(self):
        return "MCTSValuePlayer [" + self.value.__name__ + "]"
        
class MCTSModelPlayer(MCTSValuePlayer):
    
    def __init__(self, player, model):
        MCTSValuePlayer.__init__(self, player, self.get_model_value)
        self.model = model
        
    def get_model_value(self, game, player):
        features = game.extractFeatures(player)
        v = self.model.get_output(features)
        v = 1 - v if self.player == game.players[0] else v
        return v
    
    def get_name(self):
        return "MCTSModelPlayer [" + self.model.get_name() +"]"
    