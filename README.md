## Terminology & Concepts

**Subject**  
A specific learning course.  
- `code`: Code written with 3–5 capitalized letters and 3–5 numbers  

**Exam**  
A specific exam/test for a subject.  
- `version`: Specific release of an exam  

**Task**  
A specific task from an exam.  
- `number`: Number (optionally with letter) that identifies the task  
- `text`: Complete formatted text for the task  

**Topics**  
Subject & exam is defined by the same category, which is chosen from a predefined list, or selected from a core topic. Tasks are defined by either a core or a sub topic.
- `main topic`: Broad academic field (defined, may be altered manually)
    - E.g: `Mathematics, Physics, Chemistry, Biology, Geoscience, Electronics, Computing, Psychology, Medicine, Society, Humanities, Education`
- `core topic`: Specific academic field
    - E.g: `Algebra, Analysis, Mechanics, Thermodynamics, Organic Chemistry, Inorganic Chemistry, Cell Biology, Genetics, Geology, Digital Systems, Programming, Cognitive Psychology, Clinical Medicine, Sociology, History, Pedagogy`
- `sub topic`: Concrete thematic topic of a task
    - E.g: `Linear Equations, Derivatives, Newton's Laws, Heat Transfer, Hydrocarbons, Periodic Table, Mitosis, DNA Replication, Plate Tectonics, Logic Gates, Data Structures, Memory Models, Perception, Mental Health, Social Structures, Ancient Civilizations, Learning Theories`

If the category of a subject is defined by a core topic, its tasks may be defined by sub topics of that core topic.
If the category of a subject is defined by a main topic, its tasks may be defined by core topics within that main topic, and the sub topics within those core topics.

**raw_text**  
Unstructured text directly extracted from PDF blocks.

**Entity (database)**  
Domain object stored as a database row.

**Object (Python)**  
Runtime instance of a class, not stored.
