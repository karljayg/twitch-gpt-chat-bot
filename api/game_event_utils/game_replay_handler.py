import logging

from settings import config


logger = logging.getLogger(__name__)

def replay_ended(self, current_game, game_player_names):
    res = ""
    winning_players = ', '.join(
        current_game.get_player_names(result_filter='Victory'))
    losing_players = ', '.join(
        current_game.get_player_names(result_filter='Defeat'))

    if len(winning_players) == 0:
        res = f"The game with {game_player_names} ended with a Tie!"
    else:

        # Compare with the threshold
        if self.total_seconds < config.ABANDONED_GAME_THRESHOLD:
            res = f"This was an abandoned game where duration was just {self.total_seconds} seconds between {game_player_names} and so {winning_players} get the free win."
            logger.debug(res)
            self.play_SC2_sound("abandoned")
        else:
            if config.STREAMER_NICKNAME in winning_players:
                self.play_SC2_sound("victory")
            else:
                self.play_SC2_sound("defeat")
            res = (f"The game with {game_player_names} ended in a win for "
                        f"{winning_players} and a loss for {losing_players}")
    return res