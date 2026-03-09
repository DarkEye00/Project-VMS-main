from django.db import migrations


def seed_induction_quiz(apps, schema_editor):
    InductionQuestion = apps.get_model("induction", "InductionQuestion")
    InductionOption = apps.get_model("induction", "InductionOption")

    quiz = [
        {
            "q": "What are the first three safety behaviors you should follow when you arrive at the workplace?",
            "marks": 1,
            "options": [
                ("Enter through the loading bay", False),
                ("Check-in, wear ID, and read safety signs", True),
                ("Proceed directly to your meeting", False),
            ],
        },
        {
            "q": "When you first arrive at Offshore Global Logistics, what is the first step you should take?",
            "marks": 1,
            "options": [
                ("Report to the main reception/security desk", True),
                ("Walk directly to the warehouse floor", False),
                ("Find a staff member in the parking lot", False),
            ],
        },
        {
            "q": "During the warehouse tour, what should visitors always do?",
            "marks": 1,
            "options": [
                ("Stay with their guide within designated walkways at all times", True),
                ("Feel free to explore side aisles", False),
                ("Take photos of all equipment", False),
            ],
        },
        {
            "q": "Who has the right of way in and around the Warehouse, especially near dispatch and receiving bays?",
            "marks": 1,
            "options": [
               
                ("Pedestrians and visitors", False),
                ("Office staff", False),
                ("Heavy machinery and forklifts", True),
            ],
        },
        {
            "q": "In case of a fire emergency, what is the correct action for visitors?",
            "marks": 1,
            "options": [
              
                ("Wait for your host to find you", False),
                ("Try to locate your personal belongings first", False),
                ("Evacuate immediately via the nearest exit to the Fire Assembly point", True),
            ],
        },
        {
            "q": "How can visitors provide feedback about safety or concerns in the facility?",
            "marks": 1,
            "options": [
                 ("Wait until they get home to email", False),
                ("Report to the Site Safety Officer or our Speak-Up Platform", True),
                ("Post it on social media", False),
               
            ],
        },
        {
            "q": "Which activities are prohibited in the warehouse?",
            "marks": 1,
            "options": [
                ("Smoking, running, and unauthorized photography", True),
                ("Wearing high-visibility vests", False),
                ("Walking on clearly marked pathways", False),
            ],
        },
        {
            "q": "Where should visitors walk inside the warehouse to ensure safety?",
            "marks": 1,
            "options": [
                ("In clearly marked pedestrian walkways", True),
                ("Anywhere that looks clear of forklifts", False),
                ("Along the center of the driving lanes", False),
            ],
        },
        {
            "q": "When climbing stairs in the facility, what is the safest practice?",
            "marks": 1,
            "options": [
                ("Always maintain using handrails", True),
                ("Move as quickly as possible to clear the way", False),
                ("Carry large items in both hands", False),
            ],
        },
    ]

    for item in quiz:
        question, _ = InductionQuestion.objects.get_or_create(
            question_text=item["q"],
            defaults={"marks": item["marks"], "is_active": True},
        )

        # Keep question config consistent if it already existed
        changed = False
        if getattr(question, "marks", None) != item["marks"]:
            question.marks = item["marks"]
            changed = True
        if getattr(question, "is_active", None) is False:
            question.is_active = True
            changed = True
        if changed:
            question.save(update_fields=["marks", "is_active"])

        # Create/update options
        for opt_text, is_correct in item["options"]:
            opt, created = InductionOption.objects.get_or_create(
                question=question,
                option_text=opt_text,
                defaults={"is_correct": is_correct},
            )
            if not created and opt.is_correct != is_correct:
                opt.is_correct = is_correct
                opt.save(update_fields=["is_correct"])


def unseed_induction_quiz(apps, schema_editor):
    """
    Reverse operation (optional): deletes ONLY the seeded questions.
    Safe if you want rollback to remove these.
    """
    InductionQuestion = apps.get_model("induction", "InductionQuestion")
    InductionOption = apps.get_model("induction", "InductionOption")

    seeded_questions = [
        "What are the first three safety behaviors you should follow when you arrive at the workplace?",
        "When you first arrive at Offshore Global Logistics, what is the first step you should take?",
        "During the warehouse tour, what should visitors always do?",
        "Who has the right of way in and around the facility, especially near dispatch and receiving bays?",
        "In case of a fire emergency, what is the correct action for visitors?",
        "How can visitors provide feedback about safety or concerns in the facility?",
        "Which activities are prohibited in the warehouse?",
        "Where should visitors walk inside the warehouse to ensure safety?",
        "When climbing stairs in the facility, what is the safest practice?",
    ]

    qs = InductionQuestion.objects.filter(question_text__in=seeded_questions)
    InductionOption.objects.filter(question__in=qs).delete()
    qs.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("induction", "0001_initial"),  # <-- change this if your latest is different
    ]

    operations = [
        migrations.RunPython(seed_induction_quiz, unseed_induction_quiz),
    ]
