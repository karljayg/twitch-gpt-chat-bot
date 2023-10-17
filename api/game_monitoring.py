import sys
import time

from settings import config
from .sc2_game_utils import handle_SC2_game_results


def monitor_game(self,contextHistory):
    previous_game = None

    while True and not self.shutdown_flag:
        try:
            current_game = self.check_SC2_game_status()
            if (current_game.get_status() == "MATCH_STARTED" or current_game.get_status() == "REPLAY_STARTED"):
                self.conversation_mode = "in_game"
            else:
                self.conversation = "normal"
            if current_game:
                if config.IGNORE_GAME_STATUS_WHILE_WATCHING_REPLAYS and current_game.isReplay:
                    pass
                else:
                    # wait so abandoned games doesnt result in false data of 0 seconds
                    time.sleep(2)
                    # self.handle_SC2_game_results(
                    #     previous_game, current_game)
                    handle_SC2_game_results(self, previous_game,
                            current_game, contextHistory)
            previous_game = current_game
            time.sleep(config.MONITOR_GAME_SLEEP_SECONDS)
            # heartbeat indicator
            print(".", end="", flush=True)
            print("testings")
        except Exception as e:
            pass

