import sys

def search_capital(args):
    states = {
        "Oregon" : "OR",
        "Alabama" : "AL",
        "New Jersey": "NJ",
        "Colorado" : "CO"
    }
    capital_cities = {
        "OR": "Salem",
        "AL": "Montgomery",
        "NJ": "Trenton",
        "CO": "Denver"
    }

    if len(args) != 2:
        return
    if args[1] in states:
        capital = states[args[1]]
        print(capital_cities[capital])
    else:
        print("Unknown state")

if __name__ == "__main__":
    search_capital(sys.argv)