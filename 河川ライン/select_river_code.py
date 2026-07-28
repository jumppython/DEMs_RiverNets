import pandas as pd



class selecter:

    def __init__(self, map_sheet: str):
        try:
            self.map_sheet = pd.read_csv(map_sheet, dtype=str)
        except Exception as e:
            print(f"[ERROR] map sheet {map_sheet} import error!")
            self.map_sheet = pd.DataFrame({"river_code": [], "river_name": []})

    def select_name(self, code: str) -> str:
        name = self.map_sheet[self.map_sheet['river_code']==code]['river_name'].values[0]
        return name

    def select_code(self, name: str) -> str:
        code = self.map_sheet[self.map_sheet['river_name']==name]['river_code'].values[0]
        return code


def select_name(code: str) -> str:
    return selecter("river_code.csv").select_name(code)


def select_code(name: str) -> str:
    return selecter("river_code.csv").select_code(name)


if __name__ == "__main__":

    my_selecter = selecter("river_code.csv")

    while True:

        args = input("please input q[quit], n[name], c[code]: ")
        if args not in ["q", "n", "c"]:
            print("not a required input!")
            continue

        if args == "q":
            break

        if args == "n":
            name = input("please input name: ")
            try:
                print(my_selecter.select_code(name))
            except Exception as e:
                print(f"there is not any code match to name: {name}")
            continue

        if args == "c":
            code = input("please input code: ")
            try:
                print(my_selecter.select_name(code))
            except Exception as e:
                print(f"there is not any name match to code: {code}")
            continue
        