from settings import config



def replay_ended(self, current_game, game_player_names, logger):
    res = ""
    winning_players = ', '.join(
        current_game.get_player_names(result_filter='Victory'))
    losing_players = ', '.join(
        current_game.get_player_names(result_filter='Defeat'))

    # Check if streamer was observing (not playing)
    streamer_playing = (config.STREAMER_NICKNAME in winning_players or 
                        config.STREAMER_NICKNAME in losing_players)

    if len(winning_players) == 0:
        res = f"The game with {game_player_names} ended with a Tie!"
    else:

        # Compare with the threshold
        if self.total_seconds < config.ABANDONED_GAME_THRESHOLD:
            res = f"This was an abandoned game where duration was just {self.total_seconds} seconds between {game_player_names} and so {winning_players} get the free win."
            logger.debug(res)
            if streamer_playing:
                self.play_SC2_sound("abandoned")
        else:
            if streamer_playing:
                if config.STREAMER_NICKNAME in winning_players:
                    self.play_SC2_sound("victory")
                else:
                    self.play_SC2_sound("defeat")
                res = (f"The game with {game_player_names} ended in a win for "
                            f"{winning_players} and a loss for {losing_players}")
            else:
                # Observer mode - neutral commentary
                res = f"[Observer] Match replay processed: {winning_players} defeated {losing_players}"
                # No sound for observed games
    return res