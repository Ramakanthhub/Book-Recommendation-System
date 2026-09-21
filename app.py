from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np

app = Flask(__name__)

# Load the data with error handling
def load_pickle(file_path):
    try:
        return pd.read_pickle(file_path)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

popular_df = load_pickle('popular.pkl')
pt = load_pickle('pt.pkl')
books = load_pickle('books.pkl')
similarity_scores = load_pickle('similarity_scores.pkl')

# Fast in-memory book lookup table for instant sub-millisecond responses
book_meta_lookup = {}
if books is not None:
    try:
        needed_titles = set()
        if pt is not None:
            needed_titles.update(pt.index)
        if popular_df is not None:
            needed_titles.update(popular_df['Book-Title'])
        sub_books = books[books['Book-Title'].isin(needed_titles)].drop_duplicates('Book-Title')
        book_meta_lookup = sub_books.set_index('Book-Title').to_dict('index')
    except Exception as e:
        print(f"Error building book lookup cache: {e}")

# Helper: Assign category tags for students to books
def get_book_categories(title):
    t_lower = title.lower()
    cats = ['all']
    if any(w in t_lower for w in ['kill', 'mockingbird', 'catcher', '1984', 'animal', 'farm', 'gatsby', 'pride', 'prejudice', 'brave new', 'flies', 'foster', 'fahrenheit', 'bleak', 'tale', 'hobbit', 'rings']):
        cats.append('classics')
    if any(w in t_lower for w in ['people', 'heaven', 'morrie', 'alchemist', 'philosophy', 'wisdom', 'mind', 'meaning', 'life', 'zen', 'tuesdays', 'ethics', 'prince']):
        cats.append('philosophy')
    if any(w in t_lower for w in ['dune', 'galaxy', 'future', 'time', 'vampire', 'ender', 'potter', 'matrix', 'robot', 'mars', 'neuromancer', 'foundation']):
        cats.append('scifi')
    if any(w in t_lower for w in ['secret', 'child', 'called', 'ashes', 'color', 'purple', 'boy', 'bones', 'angela', 'society', 'human', 'women', 'glass']):
        cats.append('society')
    if any(w in t_lower for w in ['vinci', 'angels', 'demons', 'silence', 'lambs', 'juror', 'case', 'conspiracy', 'detective', 'firm', 'pelican', 'client']):
        cats.append('mystery')
    return ' '.join(cats)

# Helper: Resolve user input to closest book in pt.index with case-insensitivity & substring match
def resolve_title(q):
    if pt is None or not q:
        return None
    q_clean = q.strip().lower()
    
    # 1. Exact case-insensitive match
    for t in pt.index:
        if t.lower() == q_clean:
            return t
            
    # 2. Starts with query
    for t in pt.index:
        if t.lower().startswith(q_clean):
            return t
            
    # 3. Substring match
    matches = [t for t in pt.index if q_clean in t.lower()]
    if matches:
        return matches[0]
        
    return None

SYLLABUS_TRACKS = [
    {
        'id': 'cs-software',
        'title': 'Computer Science & Software Foundations',
        'badge': 'Tech & Coding',
        'description': 'Master the mental models of computation, clean code craft, and algorithmic thinking.',
        'books': [
            {
                'step': '01',
                'title': 'Code: The Hidden Language of Computer Hardware and Software',
                'author': 'Charles Petzold',
                'level': 'Beginner',
                'pages': 400,
                'est_hours': 8,
                'description': 'A mind-expanding breakdown of how electricity becomes logic, memory, and code.'
            },
            {
                'step': '02',
                'title': 'Clean Code: A Handbook of Agile Software Craftsmanship',
                'author': 'Robert C. Martin',
                'level': 'Intermediate',
                'pages': 464,
                'est_hours': 9,
                'description': 'The industry standard on writing maintainable, professional, and elegant software.'
            },
            {
                'step': '03',
                'title': 'The Pragmatic Programmer: Your Journey To Mastery',
                'author': 'Andrew Hunt, David Thomas',
                'level': 'Intermediate',
                'pages': 352,
                'est_hours': 7,
                'description': 'Practical career philosophies for engineering excellence and problem-solving.'
            },
            {
                'step': '04',
                'title': 'Introduction to Algorithms',
                'author': 'Thomas H. Cormen',
                'level': 'Advanced',
                'pages': 1312,
                'est_hours': 26,
                'description': 'The definitive rigorous mathematical foundation for data structures and algorithms.'
            }
        ]
    },
    {
        'id': 'data-ai',
        'title': 'Data Science, Machine Learning & AI',
        'badge': 'AI & Applied Math',
        'description': 'From statistical literacy and exploratory data analysis to modern deep neural networks.',
        'books': [
            {
                'step': '01',
                'title': 'Weapons of Math Destruction',
                'author': "Cathy O'Neil",
                'level': 'Beginner',
                'pages': 272,
                'est_hours': 5,
                'description': 'Essential reading on algorithmic bias, social impact, and mathematical ethics.'
            },
            {
                'step': '02',
                'title': 'Python for Data Analysis',
                'author': 'Wes McKinney',
                'level': 'Intermediate',
                'pages': 544,
                'est_hours': 11,
                'description': 'Written by the creator of pandas; the hands-on manual for data wrangling.'
            },
            {
                'step': '03',
                'title': 'Hands-On Machine Learning with Scikit-Learn and TensorFlow',
                'author': 'Aurélien Géron',
                'level': 'Intermediate',
                'pages': 856,
                'est_hours': 17,
                'description': 'The gold standard project-based textbook for implementing ML algorithms.'
            },
            {
                'step': '04',
                'title': 'Deep Learning',
                'author': 'Ian Goodfellow, Yoshua Bengio',
                'level': 'Advanced',
                'pages': 800,
                'est_hours': 16,
                'description': 'The MIT Press textbook on mathematical and theoretical foundations of deep models.'
            }
        ]
    },
    {
        'id': 'econ-finance',
        'title': 'Economics, Markets & Behavioral Finance',
        'badge': 'Business & Markets',
        'description': 'Understand how incentives, cognitive biases, and macro trends shape economies.',
        'books': [
            {
                'step': '01',
                'title': 'Naked Economics: Undressing the Dismal Science',
                'author': 'Charles Wheelan',
                'level': 'Beginner',
                'pages': 384,
                'est_hours': 8,
                'description': 'The most intuitive, equation-free introduction to trade, markets, and monetary policy.'
            },
            {
                'step': '02',
                'title': 'Freakonomics: A Rogue Economist Explores the Hidden Side of Everything',
                'author': 'Steven D. Levitt, Stephen J. Dubner',
                'level': 'Beginner',
                'pages': 352,
                'est_hours': 7,
                'description': 'Shows how statistical econometrics reveals the hidden mechanics of real life.'
            },
            {
                'step': '03',
                'title': 'Thinking, Fast and Slow',
                'author': 'Daniel Kahneman',
                'level': 'Intermediate',
                'pages': 512,
                'est_hours': 10,
                'description': 'Nobel laureate exploration of cognitive heuristics, loss aversion, and intuition.'
            },
            {
                'step': '04',
                'title': 'The Intelligent Investor',
                'author': 'Benjamin Graham',
                'level': 'Advanced',
                'pages': 640,
                'est_hours': 13,
                'description': 'The foundational classic of value investing and long-term capital allocation.'
            }
        ]
    },
    {
        'id': 'world-lit',
        'title': 'Essential World Classics & Critical Analysis',
        'badge': 'Humanities & Classics',
        'description': 'Foundational literature exploring power, dystopian governance, and human condition.',
        'books': [
            {
                'step': '01',
                'title': 'Animal Farm',
                'author': 'George Orwell',
                'level': 'Beginner',
                'pages': 144,
                'est_hours': 3,
                'description': 'The quintessential political allegory examining authoritarian corruption.'
            },
            {
                'step': '02',
                'title': '1984',
                'author': 'George Orwell',
                'level': 'Intermediate',
                'pages': 328,
                'est_hours': 7,
                'description': 'The definitive study of surveillance, truth manipulation, and language censorship.'
            },
            {
                'step': '03',
                'title': 'To Kill a Mockingbird',
                'author': 'Harper Lee',
                'level': 'Intermediate',
                'pages': 336,
                'est_hours': 7,
                'description': 'Masterwork on moral integrity, racial injustice, and empathy in the American South.'
            },
            {
                'step': '04',
                'title': 'Brave New World',
                'author': 'Aldous Huxley',
                'level': 'Intermediate',
                'pages': 288,
                'est_hours': 6,
                'description': 'Visionary exploration of technological pacification, pleasure, and biological control.'
            },
            {
                'step': '05',
                'title': 'The Catcher in the Rye',
                'author': 'J.D. Salinger',
                'level': 'Intermediate',
                'pages': 277,
                'est_hours': 6,
                'description': 'The iconic examination of adolescent alienation, grief, and societal phoniness.'
            }
        ]
    },
    {
        'id': 'study-skills',
        'title': 'Cognitive Science & Academic Study Mastery',
        'badge': 'Learning How to Learn',
        'description': 'Evidence-based cognitive science techniques to retain 3x more and study in fewer hours.',
        'books': [
            {
                'step': '01',
                'title': 'Make It Stick: The Science of Successful Learning',
                'author': 'Peter C. Brown, Henry L. Roediger',
                'level': 'Beginner',
                'pages': 336,
                'est_hours': 7,
                'description': 'Proven cognitive psychology techniques: active retrieval, interleaving, and spaced practice.'
            },
            {
                'step': '02',
                'title': 'A Mind for Numbers: How to Excel at Math and Science',
                'author': 'Barbara Oakley',
                'level': 'Beginner',
                'pages': 336,
                'est_hours': 7,
                'description': 'Techniques for shifting between focused and diffuse modes to conquer STEM subjects.'
            },
            {
                'step': '03',
                'title': 'Deep Work: Rules for Focused Success in a Distracted World',
                'author': 'Cal Newport',
                'level': 'Intermediate',
                'pages': 304,
                'est_hours': 6,
                'description': 'A blueprint for undistracted cognitive output in an era of digital distraction.'
            },
            {
                'step': '04',
                'title': 'Atomic Habits',
                'author': 'James Clear',
                'level': 'Beginner',
                'pages': 320,
                'est_hours': 6,
                'description': 'Systematic framework for building automatic, compounded academic habits.'
            }
        ]
    }
]

@app.route('/')
def index():
    if popular_df is not None:
        books_list = []
        for _, row in popular_df.iterrows():
            title = row['Book-Title']
            meta = book_meta_lookup.get(title, {})
            books_list.append({
                'name': title,
                'author': row['Book-Author'],
                'image': row['Image-URL-M'],
                'votes': int(row['num_ratings']),
                'rating': round(float(row['avg_rating']), 1),
                'year': meta.get('Year-Of-Publication', ''),
                'publisher': meta.get('Publisher', ''),
                'categories': get_book_categories(title)
            })
        return render_template('index.html', books=books_list)
    else:
        return "Error loading popular books data."

@app.route('/recommend')
def recommend_ui():
    return render_template('recommend.html')

STUDY_GOALS = [
    {
        'id': 'tech-careers',
        'title': 'Crush Software Engineering & Coding Interviews',
        'badge': 'Tech & CS',
        'tagline': 'From computational fundamentals to algorithmic mastery for top tech careers.',
        'stages': [
            {
                'stage': 'Stage 1: Foundational Mental Models',
                'title': 'Code: The Hidden Language of Computer Hardware and Software',
                'author': 'Charles Petzold',
                'description': 'Understand how transistors, logic gates, and machine instructions work from scratch.',
                'est_weeks': '2 Weeks'
            },
            {
                'stage': 'Stage 2: Engineering Craft',
                'title': 'The Pragmatic Programmer: Your Journey To Mastery',
                'author': 'Andrew Hunt, David Thomas',
                'description': 'Internalize architecture, debugging philosophies, and clean design patterns.',
                'est_weeks': '3 Weeks'
            },
            {
                'stage': 'Stage 3: Algorithmic Rigor',
                'title': 'Introduction to Algorithms',
                'author': 'Thomas H. Cormen',
                'description': 'Master dynamic programming, graph theory, trees, and asymptotic time complexity.',
                'est_weeks': '6 Weeks'
            }
        ]
    },
    {
        'id': 'data-ai-mastery',
        'title': 'Master Modern AI, Machine Learning & Data Science',
        'badge': 'Data Science & Math',
        'tagline': 'Build practical proficiency with statistical modeling, predictive algorithms, and deep neural nets.',
        'stages': [
            {
                'stage': 'Stage 1: Statistical Ethics & Data Literacy',
                'title': 'Weapons of Math Destruction',
                'author': "Cathy O'Neil",
                'description': 'Learn how algorithms impact society, bias in training sets, and real-world metrics.',
                'est_weeks': '2 Weeks'
            },
            {
                'stage': 'Stage 2: Hands-On Machine Learning',
                'title': 'Hands-On Machine Learning with Scikit-Learn and TensorFlow',
                'author': 'Aurélien Géron',
                'description': 'Implement regression, classification, random forests, and gradient boosting.',
                'est_weeks': '5 Weeks'
            },
            {
                'stage': 'Stage 3: Deep Representation Learning',
                'title': 'Deep Learning',
                'author': 'Ian Goodfellow, Yoshua Bengio',
                'description': 'Rigorous mathematical understanding of convolutional and recurrent neural networks.',
                'est_weeks': '6 Weeks'
            }
        ]
    },
    {
        'id': 'econ-finance-strategy',
        'title': 'Ace Micro & Macroeconomics and Financial Markets',
        'badge': 'Finance & Strategy',
        'tagline': 'Understand incentives, game theory, behavioral psychology, and capital allocation.',
        'stages': [
            {
                'stage': 'Stage 1: Intuitive Economics',
                'title': 'Naked Economics: Undressing the Dismal Science',
                'author': 'Charles Wheelan',
                'description': 'Master supply, demand, inflation, trade deficits, and interest rates without math friction.',
                'est_weeks': '2 Weeks'
            },
            {
                'stage': 'Stage 2: Behavioral Biases & Decision Science',
                'title': 'Thinking, Fast and Slow',
                'author': 'Daniel Kahneman',
                'description': 'Understand loss aversion, cognitive heuristics, and prospect theory for exams.',
                'est_weeks': '4 Weeks'
            },
            {
                'stage': 'Stage 3: Investment Strategy',
                'title': 'The Intelligent Investor',
                'author': 'Benjamin Graham',
                'description': 'Internalize margin of safety, corporate valuation, and macroeconomic cycles.',
                'est_weeks': '4 Weeks'
            }
        ]
    },
    {
        'id': 'study-habits-finals',
        'title': 'Ace University Exams & Learn Anything 3x Faster',
        'badge': 'Study Skills & GPA',
        'tagline': 'Evidence-based cognitive science techniques to retain more information in fewer study hours.',
        'stages': [
            {
                'stage': 'Stage 1: Cognitive Science of Retention',
                'title': 'Make It Stick: The Science of Successful Learning',
                'author': 'Peter C. Brown',
                'description': 'Harness active retrieval, spaced repetition, and interleaving for midterm prep.',
                'est_weeks': '2 Weeks'
            },
            {
                'stage': 'Stage 2: STEM Problem Solving',
                'title': 'A Mind for Numbers: How to Excel at Math and Science',
                'author': 'Barbara Oakley',
                'description': 'Conquer complex math & physics proofs by alternating focused and diffuse modes.',
                'est_weeks': '2 Weeks'
            },
            {
                'stage': 'Stage 3: Deep Focus Architecture',
                'title': 'Deep Work: Rules for Focused Success in a Distracted World',
                'author': 'Cal Newport',
                'description': 'Eliminate academic procrastination and structure 4-hour high-output study blocks.',
                'est_weeks': '2 Weeks'
            }
        ]
    },
    {
        'id': 'dystopian-politics',
        'title': 'Analyze Political Power, Propaganda & Civil Liberties',
        'badge': 'Political Science & Law',
        'tagline': 'The ultimate literary sequence on authoritarian control, free thought, and civil resistance.',
        'stages': [
            {
                'stage': 'Stage 1: Rhetoric & Political Corruption',
                'title': 'Animal Farm',
                'author': 'George Orwell',
                'description': 'An allegorical study of how revolutionary ideals are subverted by propaganda.',
                'est_weeks': '1 Week'
            },
            {
                'stage': 'Stage 2: Total Surveillance & Truth Control',
                'title': '1984',
                'author': 'George Orwell',
                'description': 'Examines state psychological conditioning, surveillance, and historical revisionism.',
                'est_weeks': '2 Weeks'
            },
            {
                'stage': 'Stage 3: Technocratic Pacification',
                'title': 'Brave New World',
                'author': 'Aldous Huxley',
                'description': 'Contrasts hard totalitarianism with control through engineered pleasure and consumerism.',
                'est_weeks': '2 Weeks'
            }
        ]
    }
]

AI_BRIEFS_KNOWLEDGE_BASE = {
    '1984': {
        'core_thesis': 'A chilling examination of state totalitarianism, psychological control, and linguistic alteration where individual thought and personal privacy are completely abolished.',
        'key_concepts': [
            'Doublethink & Cognitive Manipulation: The power of holding two contradictory beliefs simultaneously.',
            'Newspeak & Linguistic Determinism: Limiting vocabulary to eliminate the very possibility of rebellious thought.',
            'Total Surveillance (Panopticon): Omnipresent monitoring through telescreens and psychological self-censorship.',
            'Manufactured Consensus: Continuous revision of historical facts to maintain absolute party infallibility.'
        ],
        'prerequisites': 'None. Highly accessible foundational reading for high school and university courses.',
        'course_relevance': 'Political Science 101, Comparative Governance, Ethics & Technology, 20th-Century World History.',
        'difficulty': 'Intermediate',
        'ai_prompts': [
            "Generate 5 essay prompts analyzing the role of Newspeak in restricting human cognition in George Orwell's 1984.",
            "Explain the psychological mechanics of 'Doublethink' with 3 modern analogies for an introductory sociology course.",
            "Compare Orwell's vision of state surveillance with modern digital data collection and algorithm-driven moderation."
        ]
    },
    'Animal Farm': {
        'core_thesis': 'An allegorical satire chronicling how idealistic revolutions degenerate into autocratic dictatorships through the manipulation of rhetoric, fear, and stratified power.',
        'key_concepts': [
            'The Cycle of Tyranny: How the oppressed, once in power, adopt the exact oppression they once fought.',
            'Rhetorical Propaganda: Squealer\'s incremental distortion of facts and moral principles.',
            'Erosion of Collective Memory: Subtle alterations to the Seven Commandments.',
            'Apathy & Complicity: How uncritical obedience enables totalitarian leadership.'
        ],
        'prerequisites': 'Basic familiarity with political revolution dynamics is helpful.',
        'course_relevance': 'Political Philosophy, Rhetoric & Critical Thinking, European History, Comparative Literature.',
        'difficulty': 'Beginner-Friendly',
        'ai_prompts': [
            "Analyze how the Seven Commandments in Animal Farm are altered step-by-step to rationalize dictator privileges.",
            "What does Squealer's character teach us about rhetorical fallacies and state-controlled information?",
            "Create a character-to-political archetype comparison table analyzing Boxer, Napoleon, and Snowball."
        ]
    },
    'To Kill a Mockingbird': {
        'core_thesis': 'A powerful examination of moral integrity, racial injustice, and empathy in the segregated American South seen through the innocent lens of youth.',
        'key_concepts': [
            'Empathy as Perspective-Taking: Learning to "climb into someone\'s skin and walk around in it."',
            'Institutional vs. Moral Justice: The divergence between legal system verdicts and objective truth.',
            'The "Mockingbird" Symbol: The destruction of innocence and gentle beings by societal cruelty.',
            'Individual Moral Conscience: Standing firm in principle against community groupthink.'
        ],
        'prerequisites': 'None. Essential text for humanities and pre-law tracks.',
        'course_relevance': 'Civil Rights History, Legal Ethics, American Literature, Sociology.',
        'difficulty': 'Intermediate',
        'ai_prompts': [
            "Discuss Atticus Finch's courtroom closing argument as a masterclass in forensic rhetoric and legal ethics.",
            "Analyze how Harper Lee uses Scout's naive narration to expose the irrationality of racial prejudice.",
            "Explain the symbolic significance of Boo Radley and Tom Robinson as dual 'mockingbirds'."
        ]
    },
    'The Hobbit : The Enchanting Prelude to The Lord of the Rings': {
        'core_thesis': 'A mythopoeic hero\'s journey demonstrating that ordinary individuals often hold the moral resilience and courage needed to balance great cosmic powers.',
        'key_concepts': [
            'The Monomyth (Hero\'s Journey): Departure, initiation, trials, and transformed return.',
            'The Corrupting Nature of Greed: Dragon-sickness and the toxic fixation on treasure (The Arkenstone).',
            'Providence vs. Luck: How unforeseen humility overcomes brute martial force.',
            'World-Building & Philology: The power of invented languages in literary immersion.'
        ],
        'prerequisites': 'None. Enjoyable for general and literature students alike.',
        'course_relevance': 'Narrative Theory, Creative Writing, Mythological Studies, Comparative Folklore.',
        'difficulty': 'Beginner-Friendly',
        'ai_prompts': [
            "Map Bilbo Baggins' character arc onto Joseph Campbell's 12 stages of the Hero's Journey.",
            "Compare Bilbo's riddle battle with Gollum to classical riddle games in Anglo-Saxon poetry.",
            "How does Tolkien contrast the rustic domesticity of the Shire with the destructive greed of Smaug?"
        ]
    },
    'The Catcher in the Rye': {
        'core_thesis': 'A poignant exploration of adolescent alienation, repressed grief, and the struggle to protect childhood innocence against the perceived phoniness of the adult world.',
        'key_concepts': [
            'Phoniness as Social Defense: Holden\'s disgust with societal posturing and insincerity.',
            'Unreliable Narration: Recognizing how unresolved trauma and bereavement distort subjective perception.',
            'The Catcher Fantasy: The desperate longing to freeze time and shield children from adult corruption.',
            'Alienation vs. Connection: The painful paradox of wanting intimacy while actively pushing people away.'
        ],
        'prerequisites': 'None.',
        'course_relevance': 'Modern American Fiction, Adolescent Psychology, Creative Writing, Mental Health Studies.',
        'difficulty': 'Intermediate',
        'ai_prompts': [
            "Analyze Holden Caulfield's unreliable narration and how his grief over Allie manifests as misanthropy.",
            "What is the symbolic meaning of the red hunting hat and the Museum of Natural History exhibits?",
            "Discuss whether Holden's critique of adult 'phoniness' remains relevant in the era of curated social media."
        ]
    },
    'Brave New World': {
        'core_thesis': 'A prescient warning that totalitarian control can be achieved not through state terror and violence, but through endless engineered pleasure, biological conditioning, and consumerist pacification.',
        'key_concepts': [
            'Hedonic Control vs. Coercion: Why citizens happily embrace servitude when doped with endless amusement (Soma).',
            'Bokanovsky\'s Process: Genetic stratification and prenatal psychological conditioning.',
            'The Elimination of Suffering & Art: Why truth, tragic beauty, and genuine love require discomfort.',
            'The Savage as Moral Foil: Confronting industrial hyper-rationalism with natural human emotion.'
        ],
        'prerequisites': 'None.',
        'course_relevance': 'Bioethics, Philosophy of Technology, Political Theory, Sociology of Consumerism.',
        'difficulty': 'Intermediate',
        'ai_prompts': [
            "Contrast Huxley's 'oppression by pleasure' in Brave New World with Orwell's 'oppression by pain' in 1984.",
            "What bioethical warnings does Brave New World raise regarding modern gene editing and psychopharmacology?",
            "Analyze the philosophical debate between Mustapha Mond and John the Savage in Chapter 16."
        ]
    }
}

def generate_dynamic_ai_brief(title, author):
    # Lookup in knowledge base with case-insensitive matching
    for key, data in AI_BRIEFS_KNOWLEDGE_BASE.items():
        if key.lower() in title.lower() or title.lower() in key.lower():
            return {
                'title': title,
                'author': author,
                'core_thesis': data['core_thesis'],
                'key_concepts': data['key_concepts'],
                'prerequisites': data['prerequisites'],
                'course_relevance': data['course_relevance'],
                'difficulty': data['difficulty'],
                'ai_prompts': data['ai_prompts']
            }

    # Synthesize an academic concept brief dynamically for catalog items
    return {
        'title': title,
        'author': author,
        'core_thesis': f'A seminal text exploring foundational themes in {title}, examining how {author} conceptualizes character dynamics, societal pressures, and human decision-making.',
        'key_concepts': [
            f'Core Theme & Thesis Development: How the author establishes narrative urgency and thematic depth.',
            f'Character Psychology & Decision Architecture: Cognitive motivations and situational ethics.',
            f'Societal & Cultural Reflections: The historical and philosophical context underpinning the work.',
            f'Stylistic & Rhetorical Devices: Narrative pacing, voice, and symbolic motifs.'
        ],
        'prerequisites': 'General undergraduate reading level; curiosity about modern narrative structures.',
        'course_relevance': 'General Humanities, Literature Electives, Critical Reading & Writing.',
        'difficulty': 'Intermediate Academic',
        'ai_prompts': [
            f"Generate a 3-paragraph executive summary of '{title}' by {author} for a college study guide.",
            f"What are the top 3 critical analytical points a student should include in an essay about '{title}'?",
            f"Create 4 active-recall practice questions covering the primary themes and characters in '{title}'."
        ]
    }

CAMPUS_BUNDLES = [
    {
        'id': 'stanford-cs',
        'title': 'Stanford CS & Algorithmic Systems Pack',
        'institution': 'Stanford University',
        'badge': '🏛️ Top Rated CS Core',
        'upvotes': 342,
        'semester': 'Autumn & Winter Semesters',
        'description': 'Curated by Stanford computer science peers: foundational algorithmic logic, state surveillance dynamics, cyber-ethics, and world-building mental models.',
        'tags': ['Algorithms', 'Tech Ethics', 'Distributed Systems', 'Pre-Internship'],
        'books': [
            {
                'title': '1984',
                'author': 'George Orwell',
                'role': 'Data Surveillance & Digital Panopticon',
                'image': 'http://images.amazon.com/images/P/0451524934.01.MZZZZZZZ.jpg',
                'rating': '4.8',
                'votes': '980'
            },
            {
                'title': 'The Hobbit : The Enchanting Prelude to The Lord of the Rings',
                'author': 'J.R.R. Tolkien',
                'role': 'Complex Systems & Algorithmic Quests',
                'image': 'http://images.amazon.com/images/P/0345339681.01.MZZZZZZZ.jpg',
                'rating': '4.9',
                'votes': '850'
            },
            {
                'title': 'Brave New World',
                'author': 'Aldous Huxley',
                'role': 'Biotechnology & Algorithmic Conditioning',
                'image': 'http://images.amazon.com/images/P/0060809833.01.MZZZZZZZ.jpg',
                'rating': '4.7',
                'votes': '650'
            },
            {
                'title': 'Fahrenheit 451',
                'author': 'Ray Bradbury',
                'role': 'Information Suppression & Cache Invalidation',
                'image': 'http://images.amazon.com/images/P/0345342968.01.MZZZZZZZ.jpg',
                'rating': '4.6',
                'votes': '710'
            }
        ]
    },
    {
        'id': 'hopkins-premed',
        'title': 'Johns Hopkins Pre-Med & Cognitive Behavioral Pack',
        'institution': 'Johns Hopkins University',
        'badge': '🩺 Pre-Health Society Pick',
        'upvotes': 289,
        'semester': 'Year 1 & 2 Medical Prep',
        'description': 'Essential reading for future physicians: human empathy under duress, adolescent psychiatric manifestations, and bioethical dilemmas in clinical medicine.',
        'tags': ['Neuroscience', 'Medical Ethics', 'Behavioral Psychology', 'MCAT Humanities'],
        'books': [
            {
                'title': 'The Catcher in the Rye',
                'author': 'J.D. Salinger',
                'role': 'Adolescent Trauma & Psychological Defense Mechanisms',
                'image': 'http://images.amazon.com/images/P/0316769487.01.MZZZZZZZ.jpg',
                'rating': '4.6',
                'votes': '780'
            },
            {
                'title': 'To Kill a Mockingbird',
                'author': 'Harper Lee',
                'role': 'Empathy, Bedside Manner & Moral Courage',
                'image': 'http://images.amazon.com/images/P/0446310786.01.MZZZZZZZ.jpg',
                'rating': '4.9',
                'votes': '1120'
            },
            {
                'title': 'Brave New World',
                'author': 'Aldous Huxley',
                'role': 'Clinical Genetics & Pharmaceutical Pacification (Soma)',
                'image': 'http://images.amazon.com/images/P/0060809833.01.MZZZZZZZ.jpg',
                'rating': '4.7',
                'votes': '650'
            },
            {
                'title': 'The Secret Life of Bees',
                'author': 'Sue Monk Kidd',
                'role': 'Social Determinants of Mental Health & Community Healing',
                'image': 'http://images.amazon.com/images/P/0142001740.01.MZZZZZZZ.jpg',
                'rating': '4.8',
                'votes': '620'
            }
        ]
    },
    {
        'id': 'harvard-prelaw',
        'title': 'Harvard & Yale Pre-Law Rhetoric & Jurisprudence Pack',
        'institution': 'Harvard Law Undergraduate Society',
        'badge': '⚖️ Moot Court Essential',
        'upvotes': 415,
        'semester': 'Constitutional Law & Moot Court',
        'description': 'Sharpen your cross-examination, legal ethics, and forensic argument skills through masterworks of institutional justice and totalitarian degradation.',
        'tags': ['Forensic Rhetoric', 'Constitutional Law', 'Legal Ethics', 'Moot Court'],
        'books': [
            {
                'title': 'To Kill a Mockingbird',
                'author': 'Harper Lee',
                'role': 'Forensic Examination, Cross-Exam & Atticus Closing Argument',
                'image': 'http://images.amazon.com/images/P/0446310786.01.MZZZZZZZ.jpg',
                'rating': '4.9',
                'votes': '1120'
            },
            {
                'title': 'Animal Farm',
                'author': 'George Orwell',
                'role': 'Constitutional Degradation, Propaganda & Statutory Shifts',
                'image': 'http://images.amazon.com/images/P/0451526341.01.MZZZZZZZ.jpg',
                'rating': '4.8',
                'votes': '890'
            },
            {
                'title': '1984',
                'author': 'George Orwell',
                'role': 'Due Process Elimination & State Panopticon',
                'image': 'http://images.amazon.com/images/P/0451524934.01.MZZZZZZZ.jpg',
                'rating': '4.8',
                'votes': '980'
            },
            {
                'title': 'The Chamber',
                'author': 'John Grisham',
                'role': 'Capital Punishment Jurisprudence & Appellate Advocacy',
                'image': 'http://images.amazon.com/images/P/0385424728.01.MZZZZZZZ.jpg',
                'rating': '4.5',
                'votes': '510'
            }
        ]
    },
    {
        'id': 'wharton-mba',
        'title': 'Wharton & Sloan MBA Strategy & Behavioral Economics Pack',
        'institution': 'Wharton Business & Economics Guild',
        'badge': '📈 MBA Strategy Choice',
        'upvotes': 378,
        'semester': 'Executive Leadership & Strategy',
        'description': 'Game theory, institutional capture, organizational incentives, and collective action failures studied through compelling socio-economic narratives.',
        'tags': ['Behavioral Economics', 'Game Theory', 'Organizational Power', 'Corporate Ethics'],
        'books': [
            {
                'title': 'Animal Farm',
                'author': 'George Orwell',
                'role': 'Organizational Capture & Executive Privilege Rationalization',
                'image': 'http://images.amazon.com/images/P/0451526341.01.MZZZZZZZ.jpg',
                'rating': '4.8',
                'votes': '890'
            },
            {
                'title': 'Lord of the Flies',
                'author': 'William Golding',
                'role': 'Social Contract Theory & Collapse of Institutional Governance',
                'image': 'http://images.amazon.com/images/P/0399501487.01.MZZZZZZZ.jpg',
                'rating': '4.7',
                'votes': '760'
            },
            {
                'title': 'The Firm',
                'author': 'John Grisham',
                'role': 'Corporate Whistleblowing & Institutional Incentive Traps',
                'image': 'http://images.amazon.com/images/P/044021145X.01.MZZZZZZZ.jpg',
                'rating': '4.6',
                'votes': '640'
            },
            {
                'title': 'Brave New World',
                'author': 'Aldous Huxley',
                'role': 'Consumer Demand Engineering & Total Hedonic Pacification',
                'image': 'http://images.amazon.com/images/P/0060809833.01.MZZZZZZZ.jpg',
                'rating': '4.7',
                'votes': '650'
            }
        ]
    }
]

FLASHCARDS_KNOWLEDGE_BASE = {
    '1984': [
        {
            'q': 'What is "Doublethink" and how does the Party use it to maintain absolute authority?',
            'a': 'Doublethink is the cognitive ability to hold two contradictory beliefs in one\'s mind simultaneously and accept both of them (e.g., "War is Peace"). It eliminates psychological dissonance and prevents critical evaluation of state policy.'
        },
        {
            'q': 'What is the primary linguistic and political purpose of "Newspeak"?',
            'a': 'Newspeak aims to progressively narrow the range of human thought. By systematically eradicating nuances, synonyms, and words capable of expressing dissent (like "free" in an intellectual sense), political heresy becomes literally impossible to conceptualize.'
        },
        {
            'q': 'What psychological transformation does Winston undergo in Room 101?',
            'a': 'Room 101 confronts the victim with their worst nightmare (for Winston, carnivorous rats). Under mortal panic, Winston sacrifices Julia ("Do it to Julia!"), destroying his final bastion of personal integrity and resulting in total subjugation to Big Brother.'
        },
        {
            'q': 'Explain the concept of the "Telescreen" in modern surveillance architecture.',
            'a': 'The telescreen represents a bidirectional surveillance terminal that broadcasts state propaganda while constantly recording audio and video. It operates on the Panopticon principle: because citizens never know when they are watched, they self-police constantly.'
        }
    ],
    'Animal Farm': [
        {
            'q': 'How does Squealer incrementally alter the Seven Commandments?',
            'a': 'Squealer modifies Commandments under cover of darkness to rationalize ruling privileges—e.g., adding "with sheets" to "No animal shall sleep in a bed" and "to excess" to "No animal shall drink alcohol," concluding with "All animals are equal, but some are more equal than others."'
        },
        {
            'q': 'What historical figure or concept does the loyal workhorse Boxer symbolize?',
            'a': 'Boxer represents the exploited, trusting working-class proletariat whose dedication ("I will work harder" and "Napoleon is always right") is weaponized by the regime until he is callously sold to the knackers when no longer productive.'
        },
        {
            'q': 'What is the literary and allegorical climax of Animal Farm\'s final scene?',
            'a': 'The other animals look through the farmhouse window from pig to man and from man to pig, and realize it has become impossible to distinguish between the human oppressors they overthrew and their new porcine rulers.'
        },
        {
            'q': 'How does Napoleon use Snowball as a scapegoat for all farm catastrophes?',
            'a': 'Napoleon attributes every setback (such as the collapsed windmill) to Snowball\'s alleged treason. This deflects blame away from executive incompetence, unites the population against an invisible external enemy, and justifies internal purges.'
        }
    ],
    'To Kill a Mockingbird': [
        {
            'q': 'What does Atticus Finch mean by saying it is a "sin to kill a mockingbird"?',
            'a': 'Mockingbirds do nothing except make music for people to enjoy; they don\'t eat crops or damage gardens. Metaphorically, harming innocent, vulnerable figures (like Tom Robinson and Boo Radley) who bring no harm to the world is a grave moral injustice.'
        },
        {
            'q': 'What is Atticus Finch\'s core rule for moral empathy and understanding others?',
            'a': '"You never really understand a person until you consider things from his point of view... until you climb into his skin and walk around in it."'
        },
        {
            'q': 'Why is the physical injury to Tom Robinson\'s left arm critical to the courtroom trial?',
            'a': 'Mayella Ewell\'s facial bruises were primarily on the right side of her face, proving her attacker led with his left hand. Tom Robinson\'s left arm was crippled from a cotton gin accident, proving physical impossibility and exposing Bob Ewell as the culprit.'
        },
        {
            'q': 'Why does Sheriff Heck Tate decide to claim Bob Ewell "fell on his own knife"?',
            'a': 'Tate realizes Boo Radley killed Ewell to protect Jem and Scout. Bringing the intensely reclusive Boo into the public trial spotlight would be subjecting an innocent savior to torment—symbolically "killing a mockingbird."'
        }
    ],
    'The Hobbit : The Enchanting Prelude to The Lord of the Rings': [
        {
            'q': 'What psychological affliction does the dragon Smaug inflict upon mortals (Dragon-sickness)?',
            'a': 'Dragon-sickness represents toxic avarice, paranoia, and possessiveness induced by hoarded wealth. It corrupts Thorin Oakenshield into risking warfare with elves and men over the Arkenstone rather than honoring honorable restitution.'
        },
        {
            'q': 'How does Bilbo Baggins win the riddle battle with Gollum?',
            'a': 'After trading classical cosmological riddles (time, dark, wind, mountain), Bilbo absentmindedly touches his pocket and asks "What have I got in my pocket?", an accidental question that stumps Gollum and secures Bilbo\'s escape.'
        },
        {
            'q': 'What thematic role does the burglar role play in Bilbo\'s character development?',
            'a': 'Hired as a modest burglar by Gandalf, Bilbo transcends conventional martial heroism. His moral courage, humility, and diplomatic initiative (such as surrendering the Arkenstone to prevent war) prove superior to brute force.'
        },
        {
            'q': 'What is the significance of the magic Ring\'s introduction in The Hobbit vs. LOTR?',
            'a': 'In The Hobbit, the Ring is presented primarily as a convenient folkloric invisibility tool. Tolkien retroactively imbued it with corrupting cosmic malice when writing The Lord of the Rings, reflecting deeper moral stakes.'
        }
    ],
    'Brave New World': [
        {
            'q': 'What is the "Bokanovsky Process" and what societal function does it serve?',
            'a': 'A method of artificial embryology where a single fertilized human egg buds into up to 96 identical twins, creating genetically standardized batches of humans predetermined for specific caste labor (Alphas down to Epsilons).'
        },
        {
            'q': 'How does "Soma" function as an instrument of state totalitarianism?',
            'a': 'Soma is an engineered euphoric and tranquilizing drug distributed by the state. Rather than using physical torture or terror, the regime pacifies dissent by instantly dissolving psychological anxiety and existential questioning into pleasure.'
        },
        {
            'q': 'What is the philosophical core of the debate between Mustapha Mond and John the Savage?',
            'a': 'Mond argues universal happiness and social stability require sacrificing art, religion, literature, and truth. John insists that genuine human nobility, passion, and morality require the right to be unhappy and experience suffering.'
        },
        {
            'q': 'What is the purpose of "Hypnopaedia" in the World State?',
            'a': 'Sleep-teaching repeatedly broadcasts caste-specific slogans into children\'s subconscious during sleep, conditioning them to love their economic station, consume manufactured goods, and despise solitude or philosophy.'
        }
    ],
    'The Catcher in the Rye': [
        {
            'q': 'What does Holden Caulfield envision as his ultimate ideal role as the "Catcher in the Rye"?',
            'a': 'He imagines thousands of children playing in a field of rye next to a cliff, and his mission would be to catch them before they fall off—a poignant metaphor for protecting children\'s innocence from falling into the corruption and "phoniness" of adulthood.'
        },
        {
            'q': 'What does Holden\'s red hunting hat symbolize throughout the novel?',
            'a': 'The hat symbolizes Holden\'s individuality, emotional vulnerability, and desire to isolate himself from society while craving warmth. He wears it backward, mirroring an eccentric shield against the adult world.'
        },
        {
            'q': 'Why is Holden obsessed with where the Central Park ducks go during winter?',
            'a': 'The ducks reflect Holden\'s anxiety about sudden change, vulnerability, and death (mirroring his brother Allie\'s sudden passing). He desperately wants reassurance that vulnerable creatures are looked after when their environment turns cold.'
        },
        {
            'q': 'What critical realization does Holden experience watching Phoebe on the carrousel?',
            'a': 'Watching Phoebe reach for the gold ring in the rain, Holden realizes you have to let children take risks and fall if they must: adulthood cannot be prevented, and letting go is an essential part of love and maturity.'
        }
    ]
}

def generate_dynamic_flashcards(title, author):
    # Lookup in knowledge base
    for key, cards in FLASHCARDS_KNOWLEDGE_BASE.items():
        if key.lower() in title.lower() or title.lower() in key.lower():
            return cards

    # Dynamic synthesis covering 4 pedagogical angles
    return [
        {
            'q': f'What is the central thesis and core conceptual premise of "{title}" by {author}?',
            'a': f'The work critically examines human decision-making, identity formation, and thematic conflict within its genre, challenging readers to question prevailing social assumptions through {author}\'s narrative architecture.'
        },
        {
            'q': f'What primary internal or external conflict drives the narrative arc in "{title}"?',
            'a': f'The protagonist and key figures must navigate structural friction between individual desires and broader societal, philosophical, or institutional expectations, testing their moral resilience and core values.'
        },
        {
            'q': f'Which key literary, historical, or analytical motif is essential for exam analysis in "{title}"?',
            'a': f'Key analytical focuses include recurring symbolic motifs, subtle shifts in narrative voice, and character foils that contrast alternative responses to ethical and existential dilemmas.'
        },
        {
            'q': f'How can students effectively cite or synthesize "{title}" in an academic paper or comparative essay?',
            'a': f'Students can utilize "{title}" as a primary case study illustrating how narrative framing influences audience empathy, perspective-taking, and ideological consensus.'
        }
    ]

@app.route('/tracks')
def tracks():
    return render_template('tracks.html', tracks=SYLLABUS_TRACKS)

@app.route('/goals')
def goals():
    return render_template('goals.html', goals=STUDY_GOALS)

@app.route('/community')
def community():
    return render_template('community.html', bundles=CAMPUS_BUNDLES)

@app.route('/shelf')
def shelf():
    return render_template('shelf.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/api/ai_brief/<path:book_title>')
def get_ai_brief(book_title):
    author = request.args.get('author', 'Academic Author')
    brief = generate_dynamic_ai_brief(book_title, author)
    return jsonify(brief)

@app.route('/api/flashcards/<path:book_title>')
def get_flashcards(book_title):
    author = request.args.get('author', 'Academic Author')
    cards = generate_dynamic_flashcards(book_title, author)
    return jsonify({
        'title': book_title,
        'author': author,
        'cards': cards
    })


@app.route('/api/search_suggestions')
def search_suggestions():
    q = request.args.get('q', '').strip().lower()
    if not q or len(q) < 2:
        return jsonify([])

    matches = []
    if pt is not None:
        # Match starting with first
        for t in pt.index:
            if t.lower().startswith(q):
                matches.append({'title': t, 'recommendable': True})
                if len(matches) >= 8:
                    break
        # Then match containing
        if len(matches) < 8:
            for t in pt.index:
                if q in t.lower() and not any(m['title'] == t for m in matches):
                    matches.append({'title': t, 'recommendable': True})
                    if len(matches) >= 8:
                        break

    return jsonify(matches)

@app.route('/recommend_books', methods=['POST'])
def recommend():
    user_input = request.form.get('user_input', '').strip()
    if not user_input:
        return render_template('recommend.html', query=None, data=[])

    matched_title = resolve_title(user_input)

    if matched_title and pt is not None and similarity_scores is not None:
        try:
            index = np.where(pt.index == matched_title)[0][0]
            similar_items = sorted(
                list(enumerate(similarity_scores[index])), 
                key=lambda x: x[1], 
                reverse=True
            )[1:6]  # top 5 similar items

            data = []
            for item in similar_items:
                book_idx = item[0]
                score = item[1]
                title = pt.index[book_idx]
                meta = book_meta_lookup.get(title, {})
                author = meta.get('Book-Author', 'Unknown Author')
                image = meta.get('Image-URL-M', '')
                year = meta.get('Year-Of-Publication', '')
                publisher = meta.get('Publisher', '')

                # Fallback to books dataframe if not in fast lookup
                if not image and books is not None:
                    temp_df = books[books['Book-Title'] == title]
                    if not temp_df.empty:
                        author = temp_df.iloc[0]['Book-Author']
                        image = temp_df.iloc[0]['Image-URL-M']
                        year = temp_df.iloc[0].get('Year-Of-Publication', '')
                        publisher = temp_df.iloc[0].get('Publisher', '')

                data.append({
                    'title': title,
                    'author': author,
                    'image': image,
                    'year': year,
                    'publisher': publisher,
                    'match_pct': int(score * 100) if score > 0 else 85
                })

            return render_template('recommend.html', query=matched_title, data=data, is_fallback=False)
        except Exception as e:
            print(f"Error during recommendation: {e}")

    # Fallback: if not found in pt, provide top popular student recommendations
    data = []
    if popular_df is not None:
        sample_pop = popular_df.head(5)
        for _, row in sample_pop.iterrows():
            data.append({
                'title': row['Book-Title'],
                'author': row['Book-Author'],
                'image': row['Image-URL-M'],
                'year': '',
                'publisher': '',
                'match_pct': None
            })

    return render_template('recommend.html', query=user_input, data=data, is_fallback=True)

if __name__ == '__main__':
    app.run(debug=True)
