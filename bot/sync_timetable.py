import json

def sync_timetable():
    with open('timetable.json', 'r') as timetable_file:
        timetable_data = json.load(timetable_file)

    with open('user.json', 'r') as user_file:
        user_data = json.load(user_file)

    timetable_subjects = {}
    for course in timetable_data['schedule']:
        for subject in course['subjects']:
            key = (subject['subCode'], subject['L'])
            if key not in timetable_subjects:
                timetable_subjects[key] = subject

    changes_made = False
    for user_id, user_subjects in user_data.items():
        for subject_group in user_subjects:
            for subject in subject_group:
                key = (subject['subCode'], subject['L'])
                if key in timetable_subjects:
                    timetable_subject = timetable_subjects[key]
                    if (subject['time'] != timetable_subject['time'] or
                        subject['lecturer'] != timetable_subject['lecturer'] or
                        subject['room'] != timetable_subject['room']):
                        subject['time'] = timetable_subject['time']
                        subject['lecturer'] = timetable_subject['lecturer']
                        subject['room'] = timetable_subject['room']
                        changes_made = True

    if changes_made:
        with open('user.json', 'w') as user_file:
            json.dump(user_data, user_file, indent=2)
        print("User data has been updated with timetable changes.")
    else:
        print("No changes were necessary. User data is up to date.")

if __name__ == "__main__":
    sync_timetable()
