from abc import ABC, abstractmethod
from Player import RandomPlayer, ModelPlayer
from CythonBackgammon import Game
import tensorflow as tf
import numpy as np
import random
import os

class NeuralNetModel(ABC): #based on https://github.com/fomorians/td-gammon
    
    def __init__(self, sess, input_size = 198, hidden_size = 40, output_size = 1, name = None, restore=False):
    
        if not name:
            name = self.get_name()
    
        #Speicherort ermitteln
        self.checkpoint_path = os.environ.get('CHECKPOINT_PATH', 'checkpoints/' + name +'/')
        
        #session
        self.sess = sess
        self.global_step = tf.Variable(0, trainable=False, name='global_step')

        # placeholders for input and target output
        self.x = tf.placeholder('float', [1, input_size], name='x')
        self.V_next = tf.placeholder('float', [1, output_size], name='V_next')

        #Zwei fully-connected, dense Layer: Ein Input-Layer (198 Units) und dann ein Hidden-Layer (40 Units)
        #Beide werden mit der sigmoid Funktion aktiviert
        prev_y = tf.layers.dense(self.x, hidden_size, activation= tf.sigmoid)
        self.V = tf.layers.dense(prev_y, output_size, activation= tf.sigmoid)
        
        # delta = V_next - V
        self.delta_op = tf.reduce_sum(self.V_next - self.V, name='delta')

        #Erstellt eine Trainings- Operation und speichert diese ab
        self.train_op = self.create_training_op()

        #Der Saver behält immer nur den neusten Checkpoint
        self.saver = tf.train.Saver(max_to_keep=1)

        #Variablen initialisieren 
        self.sess.run(tf.global_variables_initializer())

        #Modell wiederherstellen falls gewünscht
        if restore:
            self.restore()

    @abstractmethod
    def create_training_op(self):
        pass
    
    @abstractmethod
    def get_name(self):
        pass
    
    """
        Bekannte Methoden aus der TD-GammonModel Klasse (004)
    """
            
        #Lädt den neusten (und auch einzigen) checkpoint 
    def restore(self):
        latest_checkpoint_path = tf.train.latest_checkpoint(self.checkpoint_path)
        if latest_checkpoint_path:
            print("Restoring checkpoint: {0}".format(latest_checkpoint_path))
            self.saver.restore(self.sess, latest_checkpoint_path)

    #Erzeugt einen Outpt für die gegebenen features x
    def get_output(self, x):
        return self.sess.run(self.V, feed_dict={ self.x: x })

    #Testet das Modell gegen den angegebenen enemyAgent
    def test(self, enemyPlayer=RandomPlayer('white'), games=100, debug=False):
        players = [ModelPlayer('black', self), enemyPlayer]
        
        winners = {'black':0, 'white':0}
        for i in range(games):
            game = Game()

            winner = game.play(players, debug=debug)
            winners[winner] += 1

            winners_total = sum(winners.values())
            print("[Game %d] %s (%s) vs %s (%s) %d:%d of %d games (%.2f%%)" % (i, \
                players[0].get_name(), players[0].player, \
                players[1].get_name(), players[1].player, \
                winners['black'], winners['white'], winners_total, \
                (winners['black'] / winners_total) * 100.0))
            
    def train(self, games, validation_interval, test_games=100):
        #Selbsttraining, Modell vs Modell
        players = [ModelPlayer('black', self), ModelPlayer('white', self)]

        for i in range(games):
            #Immer wieder zwischendurch testen und den Fortschritt speichern
            if i != 0 and i % validation_interval == 0:
                self.saver.save(self.sess, self.checkpoint_path + 'checkpoint.ckpt', global_step=global_step)
                print("Progress saved!")
                self.test(games = test_games)

            #Spiel initialisieren
            game = Game()
            player_num = random.randint(0, 1)
            
            x = game.extractFeatures(players[player_num].player)

            #Spiel spielen bis es einen Sieger gibt
            game_step = 0
            while not game.get_winner():
                game.next_step(players[player_num], player_num)
                player_num = (player_num + 1) % 2

                #Das Modell mit jeden Schritt im Spiel trainieren
                x_next = game.extractFeatures(players[player_num].player)
                V_next = self.get_output(x_next)
                
                self.sess.run([self.train_op, self.delta_op], feed_dict={ self.x: x, self.V_next: V_next })

                x = x_next
                game_step += 1

            #Gewinner ermitteln
            winner = 0 if game.get_winner() == game.players[0] else 1

            #Zu guter letzt reinforcement learning: Dem Modell noch eine "Belohnung" geben, wenn es gewonnen hat
            _, global_step = self.sess.run([
                self.train_op,
                self.global_step,
            ], feed_dict={ self.x: x, self.V_next: np.array([[winner]], dtype='float') })

            #Konsolenausgabe hübsch aufbereiten
            print("Game %d/%d (Winner: %s) in %d turns" % (i, games, players[winner].player, game_step))
        #Am Ende noch mal speichern und 100 testen!
        self.saver.save(self.sess, self.checkpoint_path + 'checkpoint.ckpt', global_step=global_step) 
        self.test(games = test_games)
        
    def print_weights_biases(self):
        var_output = self.sess.run(tf.trainable_variables())
        print("Input weights", var_output[0].shape, ":\n", var_output[0])
        print("Hidden bias", var_output[1].shape, ":\n", var_output[1])
        print("Hidden weights", var_output[2].shape, ":\n", var_output[2])
        print("Output bias", var_output[3].shape, ":\n", var_output[3])
        
"""
	Implementationen dieser Abstrakten Klasse
"""

class TDGammonModel(NeuralNetModel):

	def create_training_op(self):
		#lambda, leider ohne b da dies ein Schlüsselwort ist
		lamda = tf.constant(0.7)

		#learning rate 
		alpha = tf.constant(0.1)
	
		#Global_step wird bei jeden aufruf von sess.run um 1 erhöht
		global_step_op = self.global_step.assign_add(1)

		# get gradients of output V wrt trainable variables (weights and biases)
		tvars = tf.trainable_variables()
		grads = tf.gradients(self.V, tvars)

		#Alle Variablen werden angepasst und mittels eligebility traces wird er Wert
		#der einzelnen Gewichte angepasst um gute bzw. schlechte Entscheidungen zu reflektieren
		apply_gradients = []

		for grad, var in zip(grads, tvars):
			# e-> = lambda * e-> + <grad of output w.r.t weights>
			trace = tf.Variable(tf.zeros(grad.get_shape()), trainable=False, name='trace')
			trace_op = trace.assign((lamda * trace) + grad)
				
			# grad with trace = alpha * delta * e
			grad_trace = alpha * self.delta_op * trace_op

			grad_apply = var.assign_add(grad_trace)
			apply_gradients.append(grad_apply)
			
		#Den global_step mitzählen lassen
		apply_gradients.append(global_step_op)

		#Alle Gradientenoperationen in einer train Operation zusammenfassen
		return tf.group(*apply_gradients, name='train')
			
	def get_name(self):
		return "TD-Gammon"
		
class TFGammonModel(NeuralNetModel):

    def create_training_op(self):
        return tf.train.GradientDescentOptimizer(0.8).minimize(self.delta_op, global_step = self.global_step)
    
    def get_name(self):
        return "TF-Gammon"

		
from NeuralNetModel import NeuralNetModel

class TFGammonModel2(NeuralNetModel):

    def create_training_op(self):
        squared_error = tf.reduce_mean(tf.squared_difference(self.V_next, self.V))
        return tf.train.GradientDescentOptimizer(0.8).minimize(squared_error, global_step = self.global_step)
    
    def get_name(self):
        return "TF-Gammon2"
