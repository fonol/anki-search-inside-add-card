# anki-search-inside-add-card
# Copyright (C) 2019 - 2020 Tom Z.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import aqt


try: 

    class AddPreviewer(aqt.previewer.BrowserPreviewer):
        """ Subclass of the browser previewer, overrides some methods to make it work in the Add dialog. """

        def __init__(self, parent, parent_window, cards):
            aqt.previewer.BrowserPreviewer.__init__(self, parent, parent_window, None)
            self._cards             = cards
            self._ix                = 0
            self._close_callback    = self._close_cb

        def card(self):
            return self._cards[self._ix]

        def _should_enable_prev(self):
            return aqt.previewer.MultiCardPreviewer._should_enable_prev(self) or self._ix > 0 

        def _should_enable_next(self):
            return aqt.previewer.MultiCardPreviewer._should_enable_next(self) or self._ix < len(self._cards) - 1

        def _on_prev_card(self):
            if self._ix > 0:
                self._ix -= 1
                self.render_card()

        def _on_next_card(self):
            self._ix += 1
            self._ix = self._ix % len(self._cards)
            self.render_card()

        def _on_finished(self, ok):
            pass

        def _close_cb(self):
            pass
except:
    pass