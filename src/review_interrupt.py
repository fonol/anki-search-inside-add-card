import state
import random
import math

from aqt import mw
from .api import try_open_first_in_queue, queue_has_items
from .dialogs.review_read_interrupt import ReviewReadInterruptDialog
from .config import get_config_value
from.notes import get_notes_scheduled_for_today

last_did = 0
current_did = 1
interrupt_in_n_cards = 0

def review_interruptor():
    global last_did, current_did, interrupt_in_n_cards

    interruption_mode = get_config_value("mix_reviews_and_reading.mode")

    if interruption_mode == "every_n":
        interrupt_in_n_cards = get_config_value("mix_reviews_and_reading.interrupt_every_nth_card")

    if interruption_mode == "due_random":
        # get number of siac notes scheduled for today
        due_siac_notes = get_notes_scheduled_for_today()
        if due_siac_notes is None:
            return
        number_siac_notes = float(len(due_siac_notes))
        # should not happen, but better safe than sorry
        if number_siac_notes == 0.0:
            return

        current_did = mw.col.decks.selected()

        # check if did has changed
        if last_did != current_did:
            last_did = current_did


            # get number of due cards for today
            counts = list(mw.col.sched.counts())
            count_new = counts[0]
            count_learn = counts[1]
            count_review = counts[2]
            due_cards = float(count_learn + count_new + count_review)

            # interrupt every n cards, add fuzz
            n_cards = due_cards/number_siac_notes
            fuzz_amount = get_config_value("mix_reviews_and_reading.fuzz")
            n_cards_fuzz = n_cards + fuzz_amount*n_cards*random.uniform(-1.0, 1.0)

            interrupt_in_n_cards = math.floor(n_cards_fuzz)

            if interrupt_in_n_cards >= due_cards:
                interrupt_in_n_cards = int(due_cards)


    state.review_counter += 1

    if state.review_counter >= interrupt_in_n_cards:
        state.review_counter = 0

        # not exactly transparent code, but will force due_random to recalculate interrupt_in_n_cards
        last_did = 0

        if queue_has_items():
            execute_review_interruption()




def execute_review_interruption():
    if get_config_value("mix_reviews_and_reading.show_dialog"):
        dialog = ReviewReadInterruptDialog(mw)
        if not dialog.exec_():
            return

    try_open_first_in_queue("Reading time!")
