import json

data = [
    {"Date": "15 April 2022", "Public holiday": "Good Friday", "Actual day of the week": "Friday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Sunday", "Nightsave Urban Small": "Sunday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Sunday"},
    {"Date": "18 April 2022", "Public holiday": "Family Day", "Actual day of the week": "Monday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Sunday", "Nightsave Urban Small": "Sunday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Sunday"},
    {"Date": "27 April 2022", "Public holiday": "Freedom Day", "Actual day of the week": "Wednesday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"},
    {"Date": "1 May 2022", "Public holiday": "Workers Day", "Actual day of the week": "Sunday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Sunday", "Nightsave Urban Small": "Sunday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Sunday"},
    {"Date": "2 May 2022", "Public holiday": "Public Holiday", "Actual day of the week": "Monday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"},
    {"Date": "16 June 2022", "Public holiday": "Youth Day", "Actual day of the week": "Thursday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"},
    {"Date": "9 August 2022", "Public holiday": "National Women's Day", "Actual day of the week": "Tuesday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"},
    {"Date": "24 September 2022", "Public holiday": "Heritage Day", "Actual day of the week": "Saturday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"},
    {"Date": "16 December 2022", "Public holiday": "Day of Reconciliation", "Actual day of the week": "Friday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"},
    {"Date": "25 December 2022", "Public holiday": "Christmas Day", "Actual day of the week": "Sunday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Sunday", "Nightsave Urban Small": "Sunday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Sunday"},
    {"Date": "26 December 2022", "Public holiday": "Day of Goodwill", "Actual day of the week": "Monday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Sunday", "Nightsave Urban Small": "Sunday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Sunday"},
    {"Date": "1 January 2023", "Public holiday": "New Year’s Day", "Actual day of the week": "Sunday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Sunday", "Nightsave Urban Small": "Sunday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Sunday"},
    {"Date": "21 March 2023", "Public holiday": "Human Rights Day", "Actual day of the week": "Tuesday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"},
    {"Date": "7 April 2023", "Public holiday": "Good Friday", "Actual day of the week": "Friday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Sunday", "Nightsave Urban Small": "Sunday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Sunday"},
    {"Date": "10 April 2023", "Public holiday": "Family Day", "Actual day of the week": "Monday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Sunday", "Nightsave Urban Small": "Sunday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Sunday"},
    {"Date": "27 April 2023", "Public holiday": "Freedom Day", "Actual day of the week": "Thursday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"},
    {"Date": "1 May 2023", "Public holiday": "Worker’s Day", "Actual day of the week": "Monday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"},
    {"Date": "16 June 2023", "Public holiday": "Youth Day", "Actual day of the week": "Friday", "TOU day treated as": "Sunday", "Nightsave Urban Large": "Saturday", "Nightsave Urban Small": "Saturday", "Megaflex, Miniflex, WEPS, Megaflex Gen": "Saturday"}
]

json_data = []

month_to_number = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}

for item in data:
    date_parts = item["Date"].split()
    day, month, year = int(date_parts[0]), date_parts[1], int(date_parts[2])
    
    treat_as = 0
    if item["Megaflex, Miniflex, WEPS, Megaflex Gen"] == "Sunday":
        treat_as = 1
    elif item["Megaflex, Miniflex, WEPS, Megaflex Gen"] == "Saturday":
        treat_as = 7

    json_entry = {
        "day": day,
        "month": month_to_number[month],
        "year": year,
        "treat_as": treat_as
    }

    json_data.append(json_entry)

json_text = json.dumps(json_data, indent=4)

print(json_text)