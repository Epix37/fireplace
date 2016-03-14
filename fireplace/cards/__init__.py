import os
from pkg_resources import resource_filename
from hearthstone import cardxml
from hearthstone.enums import CardType
from ..logging import log
from ..rules import POISONOUS
from ..utils import get_script_definition


class CardDB(dict):
	def __init__(self, filename):
		self.filename = filename
		self.initialized = False

	@staticmethod
	def merge(id, card):
		"""
		Find the xmlcard and the card definition of \a id
		Then return a merged class of the two
		"""
		carddef = get_script_definition(id)
		if carddef:
			card.scripts = type(id, (carddef, ), {})
		else:
			card.scripts = type(id, (), {})

		scriptnames = (
			"activate", "combo", "deathrattle", "draw", "inspire", "play",
			"enrage", "update", "powered_up"
		)

		for script in scriptnames:
			actions = getattr(card.scripts, script, None)
			if actions is None:
				# Set the action by default to avoid runtime hasattr() calls
				setattr(card.scripts, script, [])
			elif not callable(actions):
				if not hasattr(actions, "__iter__"):
					# Ensure the actions are always iterable
					setattr(card.scripts, script, (actions, ))

		for script in ("events", "secret"):
			events = getattr(card.scripts, script, None)
			if events is None:
				setattr(card.scripts, script, [])
			elif not hasattr(events, "__iter__"):
				setattr(card.scripts, script, [events])

		if not hasattr(card.scripts, "cost_mod"):
			card.scripts.cost_mod = None

		if not hasattr(card.scripts, "Hand"):
			card.scripts.Hand = type("Hand", (), {})

		if not hasattr(card.scripts.Hand, "events"):
			card.scripts.Hand.events = []

		if not hasattr(card.scripts.Hand.events, "__iter__"):
			card.scripts.Hand.events = [card.scripts.Hand.events]

		if not hasattr(card.scripts.Hand, "update"):
			card.scripts.Hand.update = ()

		if not hasattr(card.scripts.Hand.update, "__iter__"):
			card.scripts.Hand.update = (card.scripts.Hand.update, )

		# Set choose one cards
		if hasattr(carddef, "choose"):
			card.choose_cards = carddef.choose[:]
		else:
			card.choose_cards = []

		if hasattr(carddef, "tags"):
			for tag, value in carddef.tags.items():
				card.tags[tag] = value

		# Set some additional events based on the base tags...
		if card.poisonous:
			card.scripts.events.append(POISONOUS)

		return card

	def initialize(self):
		log.info("Initializing card database")
		self.initialized = True
		if not os.path.exists(self.filename):
			raise RuntimeError("%r does not exist. Create it with `bootstrap`." % (self.filename))

		db, xml = cardxml.load(self.filename)
		for id, card in db.items():
			self[id] = self.merge(id, card)

		log.info("Merged %i cards", len(self))

	def filter(self, **kwargs):
		"""
		Returns a list of card IDs matching the given filters. Each filter, if not
		None, is matched against the registered card database.
		cards.
		Examples arguments:
		\a collectible: Whether the card is collectible or not.
		\a type: The type of the card (hearthstone.enums.CardType)
		\a race: The race (tribe) of the card (hearthstone.enums.Race)
		\a rarity: The rarity of the card (hearthstone.enums.Rarity)
		\a cost: The mana cost of the card
		"""
		if not self.initialized:
			self.initialize()

		cards = self.values()

		if "type" not in kwargs:
			kwargs["type"] = [CardType.SPELL, CardType.WEAPON, CardType.MINION]

		for attr, value in kwargs.items():
			if value is not None:
				# What? this doesn't work?
				# cards = __builtins__["filter"](lambda c: getattr(c, attr) == value, cards)
				cards = [
					card for card in cards if (isinstance(value, list) and getattr(card, attr) in value) or
					getattr(card, attr) == value
				]

		return [card.id for card in cards]


# Here we import every card from every set and load the cardxml database.
# For every card, we will "merge" the class with its Python definition if
# it exists.
if "db" not in globals():
	xmlfile = resource_filename("fireplace", "CardDefs.xml")
	db = CardDB(xmlfile)
	filter = db.filter
