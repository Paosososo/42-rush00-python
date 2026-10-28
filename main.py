import os
import sys



def clear_screen():
    """Clears the terminal screen for a clean UI look."""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_greeting():
    clear_screen()
    print("=== GREETING SECTION ===")
    print("\nHello! Welcome to the Python CLI Main Menu demo.")
    input("\nPress Enter to return to the main menu...")

def calculate_sum():
    clear_screen()
    print("=== CALCULATE SUM ===")
    try:
        num1 = float(input("\nEnter first number: "))
        num2 = float(input("Enter second number: "))
        print(f"\nThe result of {num1} + {num2} is: {num1 + num2}")
    except ValueError:
        print("\n[Error] Invalid input. Please enter numbers only.")
    
    input("\nPress Enter to return to the main menu...")

def under_construct():
    clear_screen()
    print("This function under construction")
    input("\nPress Enter to return to the main menu...")

def display_menu():
    """Prints the actual main menu layout."""
    clear_screen()
    print("=====================================")
    print("             MAIN MENU               ")
    print("=====================================")
    print(" 1. Add Transaction")
    print(" 2. View Transactions")
    print(" 3. Edit / Delete Transaction")
    print(" 4. Search & Filter")
    print(" 5. Financial Summary")
    print(" 6. Cash Runway Prediction")
    print(" 7. Can I Afford It?")
    print(" 0. Exit Program")
    print("=====================================")

def main():
    while True:
        display_menu()
        choice = input("Select an option (0-7): ").strip()

        match choice:
            case "1":
                show_greeting()
            case "2":
                calculate_sum()
            case "0":
                clear_screen()
                print("Exiting program. Goodbye!\n")
                sys.exit()
            case _:
                under_construct()

if __name__ == '__main__':
    main()
