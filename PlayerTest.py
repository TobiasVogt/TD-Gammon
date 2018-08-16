import time
from CythonBackgammon import Game 
	
# Testfunktion für Player

def test(players, games=100, debug=False):
    wins = {Game.PLAYERS[0] : 0, Game.PLAYERS[1] : 0}
    # Zeit messen und Spielen, diesmal ohne loggen
    start = time.time()
    for i in range(games):
        game = Game()
        winner = game.play(players, debug=debug)
        wins[winner] += 1
        win_num = 0 if winner == game.players[0] else 1
        print("Spiel", i, "von", games ,"geht an", players[win_num].get_name(), "(" , winner , ")")
    end = time.time()

    # Hübsch ausgeben
    print()
    print(wins)
    print(players[0].get_name(), 'vs.' , players[1].get_name(), ':', wins['black']/games * 100, '%')
    print(games, "Spiele in ", end - start, "Sekunden")
