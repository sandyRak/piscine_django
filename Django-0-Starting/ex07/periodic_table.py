def read_elements(filename):
    elements = []

    with open(filename, "r") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            name, data = line.split(" = ")

            data = data.split(", ")

            position = int(data[0].split(":")[1])
            number = int(data[1].split(":")[1])
            symbol = data[2].split(":")[1]
            molar = data[3].split(":")[1]
            electron = data[4].split(":")[1]

            element = {
                "name": name,
                "position": position,
                "number": number,
                "symbol": symbol,
                "molar": molar,
                "electron": electron
            }

            elements.append(element)

    return elements


def get_period(number):
    if number <= 2:
        return 1
    elif number <= 10:
        return 2
    elif number <= 18:
        return 3
    elif number <= 36:
        return 4
    elif number <= 54:
        return 5
    elif number <= 86:
        return 6
    else:
        return 7


def create_html(elements):
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Periodic Table of the Elements</title>
    <style>
        body {
            font-family: Arial, sans-serif;
        }

        table {
            border-collapse: collapse;
            margin: 20px auto;
        }

        td {
            border: 1px solid black;
            width: 100px;
            height: 130px;
            vertical-align: top;
            padding: 5px;
        }

        h1 {
            text-align: center;
        }

        h4 {
            margin: 0 0 10px 0;
        }

        ul {
            margin: 0;
            padding-left: 20px;
        }
    </style>
</head>
<body>

<h1>Periodic Table of the Elements</h1>

<table>
"""

    # 7 periods
    for period in range(1, 8):
        html += "    <tr>\n"

        # 18 groups
        for position in range(18):
            element_found = None

            for element in elements:
                if (get_period(element["number"]) == period
                        and element["position"] == position):
                    element_found = element
                    break

            if element_found is None:
                html += "        <td></td>\n"
            else:
                html += "        <td>\n"
                html += "            <h4>" + element_found["name"] + "</h4>\n"
                html += "            <ul>\n"
                html += "                <li>No " + str(element_found["number"]) + "</li>\n"
                html += "                <li>" + element_found["symbol"] + "</li>\n"
                html += "                <li>" + element_found["molar"] + "</li>\n"
                html += "                <li>" + element_found["electron"] + " electrons</li>\n"
                html += "            </ul>\n"
                html += "        </td>\n"

        html += "    </tr>\n"

    html += """</table>

</body>
</html>
"""

    with open("periodic_table.html", "w") as file:
        file.write(html)


def periodic_table(filename):
    elements = read_elements(filename)
    create_html(elements)


if __name__ == "__main__":
    periodic_table("periodic_table.txt")