# SYKL Math Question Generation Guide for 4th Grade

## JSON Output Structure
Each question should be formatted as follows:

```json
{
  "opgave_number": "1",
  "sykl_del_type": "A",
  "title": "[Activity Title]",
  "materials": "[Required Materials]",
  "main_question": "[Main Task Description]",
  "sykl_del_a": "[SYKL-DEL A Question]",
  "bullet_points": "[Bullet Point 1]\n[Bullet Point 2]",
  "tips_1": "[First MATEMA-TIP]",
  "tips_2": "[Second MATEMA-TIP]",
  "tips_3": "[Third MATEMA-TIP]"
}
```

For SYKL-DEL B, use:
```json
{
  "opgave_number": "1",
  "sykl_del_type": "B",
  "title": "[Same Activity Title]",
  "materials": "[Required Materials]",
  "main_question": "[Same Main Task Description]",
  "sykl_del_b": "[SYKL-DEL B Question]",
  "bullet_points": "[Advanced Bullet Point 1]\n[Advanced Bullet Point 2]",
  "tips_1": "[First Advanced MATEMA-TIP]",
  "tips_2": "[Second Advanced MATEMA-TIP]",
  "tips_3": "[Third Advanced MATEMA-TIP]"
}
```

## Question Components Guide

### Basic Elements
1. **opgave_number**: Sequential number of the task
2. **sykl_del_type**: Either "A" or "B"
3. **title**: Brief, descriptive title of the activity
4. **materials**: List of required materials (if any)

### Content Elements
1. **main_question** should:
   - Describe the initial setup
   - Explain the basic pattern or task
   - Be clear and concrete
   - Use everyday situations or objects

2. **sykl_del_a**/**sykl_del_b** should:
   - For A: Ask open-ended questions that encourage exploration, multiple solution paths, and different approaches to problem-solving. Focus on "how" and "why" questions rather than just "what". Encourage students to explain their reasoning.
   - For B: Ask open-ended questions that encourage deeper understanding, critical thinking, and creative solutions. These questions should challenge students to generalize, make connections, and apply their knowledge in novel ways. Encourage students to justify their solutions and explore alternative approaches.

3. **bullet_points** should:
   - Be specific, measurable tasks
   - Progress in difficulty
   - Be separated by "\n" in the JSON

4. **tips_1,2,3** should:
   - Progress from general to specific guidance
   - Help students discover solutions independently
   - Build upon each other

## Example Questions with JSON

### Pattern Example (DEL A):
```json
{
  "opgave_number": "1",
  "sykl_del_type": "A",
  "title": "Tændstik Figurer",
  "materials": "Tændstikker eller pinde",
  "main_question": "I skal bygge trekanter med tændstikker. Den første trekant bruger 3 tændstikker. Når I bygger den næste trekant ved siden af, deler de en side, så I kun skal bruge 2 nye tændstikker.",
  "sykl_del_a": "Hvor mange tændstikker skal I bruge til:",
  "bullet_points": "At bygge 3 trekanter på række?\nAt bygge 4 trekanter på række?",
  "tips_1": "Start med at bygge de første to trekanter og tæl tændstikkerne.",
  "tips_2": "Se på hvor mange nye tændstikker I bruger for hver ny trekant.",
  "tips_3": "Lav en tabel der viser antallet af tændstikker for hver ny trekant."
}
```

### Pattern Example (DEL B):
```json
{
  "opgave_number": "1",
  "sykl_del_type": "B",
  "title": "Tændstik Figurer",
  "materials": "Tændstikker eller pinde",
  "main_question": "I skal bygge trekanter med tændstikker. Den første trekant bruger 3 tændstikker. Når I bygger den næste trekant ved siden af, deler de en side, så I kun skal bruge 2 nye tændstikker.",
  "sykl_del_b": "Undersøg mønsteret nærmere:",
  "bullet_points": "Hvor mange tændstikker skal I bruge til 10 trekanter?\nKan I finde en regel for at beregne antal tændstikker til et vilkårligt antal trekanter?",
  "tips_1": "Lav en tabel der viser sammenhængen mellem antal trekanter og antal tændstikker.",
  "tips_2": "Se efter et mønster i hvordan antallet af tændstikker vokser.",
  "tips_3": "Prøv at skrive en formel der virker for alle antal trekanter."
}
```

## Topic Ideas with Sample Questions
Here are some topic areas with suggested progressions from DEL A to DEL B:

1. **Geometric Patterns**
   - A: Direct counting and construction
   - B: Finding rules and formulas

2. **Measurement**
   - A: Direct measurement tasks
   - B: Unit conversions and relationships

3. **Money Calculations**
   - A: Basic addition/subtraction
   - B: Percentages and comparisons

4. **Area and Perimeter**
   - A: Counting squares/units
   - B: Finding patterns and formulas

## Question Quality Checklist
Before finalizing your JSON:
- [ ] Are all required fields filled?
- [ ] Is the main_question clear and concrete?
- [ ] Do bullet points progress logically?
- [ ] Are MATEMA-TIPS helpful and progressive?
- [ ] Does DEL B build meaningfully on DEL A?
- [ ] Is all text properly formatted for JSON?
- [ ] Are newlines properly indicated with \n?
- [ ] Are the questions open-ended and encourage creative problem-solving?
