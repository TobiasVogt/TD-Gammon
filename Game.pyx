
import time

def bench():
    cdef int i
    wins = {Game.PLAYERS[0] : 0, Game.PLAYERS[1] : 0}
    
    players = [RandomPlayer(Game.PLAYERS[0]), RandomPlayer(Game.PLAYERS[1])]

    # Zeit messen und Spielen, diesmal ohne loggen
    start = time.time()
    for i in range(1000):
        game = Game()
        winner = game.play(players, debug=False)
        wins[winner] += 1
        #print("Spiel", i, "geht an", winner)
    end = time.time()

    # Hübsch ausgeben
    print(wins)
    print("1000 Spiele in ", end - start, "Sekunden")
    
bench()