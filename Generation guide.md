SYKL Math Question Generation Guide for 4th Grade

JSON Output Structure
Each question should be formatted as follows:

json
Copy
Edit
{
  "opgave_number": "<Task number>",
  "sykl_del_type": "<A or B>",
  "title": "<Activity Title>",
  "materials": "<Required Materials>",
  "main_question": "<Central problem description>",
  "sykl_del_a": "<SYKL-DEL A question>",
  "bullet_points": "<Specific sub-questions>",
  "tips_1": "<First MATEMA-TIP>",
  "tips_2": "<Second MATEMA-TIP>",
  "tips_3": "<Third MATEMA-TIP>"
}
For SYKL-DEL B, use:

json
Copy
Edit
{
  "opgave_number": "<Task number>",
  "sykl_del_type": "B",
  "title": "<Same Activity Title>",
  "materials": "<Required Materials>",
  "main_question": "<Same main task description>",
  "sykl_del_b": "<SYKL-DEL B question>",
  "bullet_points": "<Specific sub-questions>",
  "tips_1": "<First advanced MATEMA-TIP>",
  "tips_2": "<Second advanced MATEMA-TIP>",
  "tips_3": "<Third advanced MATEMA-TIP>"
}
Question Components Guide
Key Fields:

opgave_number: Sequential number of the task.
sykl_del_type: Either "A" or "B".
title: Descriptive title summarizing the task.
materials: Materials required for the task (optional).
Content Guidelines:

main_question:

Describe the scenario or task setup clearly.
Relate it to real-world or concrete examples when possible.
Use simple language that 4th graders can understand.
sykl_del_a/sykl_del_b:

A: Focus on concrete exploration or problem-solving.
B: Push for generalization, rules, or deeper understanding.
bullet_points:

Present sequentially scaffolded sub-tasks.
Separate items using \n in JSON format.
tips_1, tips_2, tips_3:

Offer hints that gradually become more explicit.
Guide students through reasoning and problem-solving without giving away the answer.
Enhanced Checklist
Before finalizing your JSON:

 Field Completeness: Are all required fields filled?
 Clarity: Is the main question age-appropriate and clear?
 Logical Progression: Do bullet points progress from simple to challenging?
 Helpful Guidance: Are the MATEMA-TIPS appropriately scaffolded?
 Consistency: Does DEL B build upon DEL A meaningfully?
 Formatting: Are all strings and newlines formatted correctly (\n)?
 Validation: Did you validate the JSON structure with an online tool?

Example JSON

SYKL-DEL A: "Hvad vil du helst?"
{
  "opgave_number": "1",
  "sykl_del_type": "A",
  "title": "Hvad vil du helst?",
  "materials": "",
  "main_question": "I skal vælge mellem to muligheder og regne ud, hvad der er mest fordelagtigt.",
  "sykl_del_a": "Hvad vil du helst:",
  "bullet_points": "Have 60% af 2 pizzaer eller 26% af 5 pizzaer?\nFå 10% af 50 DKK eller 75% af 8 DKK?\nBlive stukket af 15% af 120 myg eller 8% af 250 myg?",
  "tips_1": "Start med at finde procentdelen af den samlede mængde.",
  "tips_2": "Sammenlign resultaterne for at finde den største eller mindste værdi.",
  "tips_3": "Tegn eller skriv tallene op, hvis det hjælper jer med at se forskellene tydeligere."
}

SYKL-DEL B: "Hvad vil du helst?"
{
  "opgave_number": "1",
  "sykl_del_type": "B",
  "title": "Hvad vil du helst?",
  "materials": "",
  "main_question": "I skal vælge mellem to muligheder og regne ud, hvad der er mest fordelagtigt.",
  "sykl_del_b": "Hvad vil du helst:",
  "bullet_points": "Hoppe med et sjippetov, der er 54% af 105 cm langt, eller 88% af 2,75 m langt?\nSidde i en trafikprop i 33% af 2 timer eller 44% af 1 time og 40 minutter?",
  "tips_1": "Start med at omregne længder og tider til samme enheder (cm eller meter, minutter eller timer).",
  "tips_2": "Regn procentdelen af de samlede længder eller tider.",
  "tips_3": "Sammenlign resultaterne og forklar, hvad I har regnet ud, og hvilken mulighed I ville vælge."
}