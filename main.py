import sys
import agent
import form

def main():
    args = sys.argv[1:]

    if len(args) != 2:
        print("If you want to specify an already existing scenario, use '-scenario n' option. Opening form...")
        scenario_number = form.execute_form()
        if scenario_number is None:
            print("The form was not completed successfully")
        a = agent.Agent()
        a.reasoning(int(scenario_number))
    else:
        if args[0] == "-scenario":
            try:
                a = agent.Agent()
                a.reasoning(int(args[1]))
            except Exception:
                print("Please introduce an existing scenario number")
        else:
            print("Please check the format: '-scenario n'")

if __name__ == '__main__':
    main()
