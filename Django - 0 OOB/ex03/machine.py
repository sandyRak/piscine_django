import random
from beverages import HotBeverage, Coffee, Tea, Chocolate, Cappuccino

class CoffeeMachine:

    class EmptyCup(HotBeverage):
        def __init__(self):
            super().__init__()
            self.price = 0.90
            self.name = "empty cup"
        
        def description(self):
            return "An empty cup?! Gimme my money back!"

    class BrokenMachineException(Exception):
        def __init__(self):
            super().__init__("This coffee machine has to be repaired.")
    
    def __init__(self):
        self.served_count = 0
        self.broken = False
    
    def repair(self):
        self.broken = False
        self.served_count = 0

    def serve(self, beverage_class):
        if self.broken:
            raise CoffeeMachine.BrokenMachineException()
        
        self.served_count += 1
        if self.served_count >= 10:
            self.broken = True
        
        if random.randint(0, 1) == 0:
            return beverage_class()
        else:
            return CoffeeMachine.EmptyCup()

def main():
    machine = CoffeeMachine()
    beverages = [Coffee, Tea, Chocolate, Cappuccino]

    for cycle in range (3):
        print("--- Cycle {} ---".format(cycle + 1))
        try:
            while True:
                beverage_class = random.choice(beverages)
                cup = machine.serve(beverage_class)
                print(cup)
                print()
        except CoffeeMachine.BrokenMachineException as e:
            print(e)
        print("Repairing the machine...\n")
        machine.repair()

if __name__ == "__main__":
    main()