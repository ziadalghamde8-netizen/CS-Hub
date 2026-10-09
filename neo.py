import os
import hashlib
import secrets
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, abort,
    request, redirect, url_for, session, flash
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

USERS_FILE = "users.txt"
VISITORS_FILE = "visitors.txt"

GUESTBOOK_FILE = "guestbook.txt"
PROGRESS_FILE = "progress.txt"

# ────────────────────────────────────────────────────────────
# QUIZ DATA — 3 questions per topic
# ────────────────────────────────────────────────────────────
QUIZZES = {
    "algorithms": [
        {"q": "What is the time complexity of binary search?",
         "options": ["O(n)", "O(log n)", "O(n²)", "O(1)"], "answer": 1},
        {"q": "Which algorithm uses a divide-and-conquer approach?",
         "options": ["Bubble sort", "Linear search", "Merge sort", "Brute force"], "answer": 2},
        {"q": "What does O(n²) typically indicate?",
         "options": ["Constant time", "Nested loops", "Logarithmic growth", "Linear time"], "answer": 1},
    ],
    "data-structures": [
        {"q": "Which structure uses LIFO ordering?",
         "options": ["Queue", "Stack", "Heap", "Tree"], "answer": 1},
        {"q": "Average lookup time in a hash table?",
         "options": ["O(n)", "O(log n)", "O(1)", "O(n²)"], "answer": 2},
        {"q": "Which tree guarantees O(log n) operations?",
         "options": ["Binary tree", "Linked list", "AVL tree", "Unbalanced BST"], "answer": 2},
    ],
    "ai-ml": [
        {"q": "Which paradigm learns from labeled data?",
         "options": ["Unsupervised", "Reinforcement", "Supervised", "Self-supervised"], "answer": 2},
        {"q": "What architecture powers GPT and Claude?",
         "options": ["CNN", "RNN", "Transformer", "SVM"], "answer": 2},
        {"q": "What does 'overfitting' mean?",
         "options": ["Too simple", "Memorizes training data", "Fast training", "Underfitting"], "answer": 1},
    ],
    "operating-systems": [
        {"q": "What does virtual memory allow?",
         "options": ["Faster CPU", "Larger address space", "More cores", "Better graphics"], "answer": 1},
        {"q": "What is a deadlock?",
         "options": ["CPU crash", "Two threads waiting on each other", "Memory leak", "Disk full"], "answer": 1},
        {"q": "Which scheduler gives each process a time slice?",
         "options": ["FCFS", "SJF", "Round Robin", "Priority"], "answer": 2},
    ],
    "networking": [
        {"q": "Which protocol is reliable and connection-oriented?",
         "options": ["UDP", "TCP", "IP", "ICMP"], "answer": 1},
        {"q": "What does DNS do?",
         "options": ["Encrypt traffic", "Translate names to IPs", "Route packets", "Assign IPs"], "answer": 1},
        {"q": "Port 443 is used by?",
         "options": ["HTTP", "FTP", "HTTPS", "SSH"], "answer": 2},
    ],
    "databases": [
        {"q": "What does ACID stand for?",
         "options": ["Atomicity, Consistency, Isolation, Durability", "Access, Cache, Index, Data", "Atomic, Clean, Integrated, Distributed", "None"], "answer": 0},
        {"q": "Which is a NoSQL database?",
         "options": ["PostgreSQL", "MySQL", "MongoDB", "SQLite"], "answer": 2},
        {"q": "CAP theorem says you can pick at most?",
         "options": ["1", "2", "3", "4"], "answer": 1},
    ],
    "semiconductor-physics": [
        {"q": "Silicon's band gap is approximately?",
         "options": ["0.5 eV", "1.12 eV", "3.4 eV", "5.0 eV"], "answer": 1},
        {"q": "N-type silicon is doped with an element having?",
         "options": ["3 valence e⁻", "4 valence e⁻", "5 valence e⁻", "6 valence e⁻"], "answer": 2},
        {"q": "A P-N junction acts as a?",
         "options": ["Resistor", "Capacitor", "Diode", "Inductor"], "answer": 2},
    ],
    "transistors": [
        {"q": "Which transistor dominates modern digital chips?",
         "options": ["BJT", "MOSFET", "JFET", "Thyristor"], "answer": 1},
        {"q": "CMOS stands for?",
         "options": ["Common MOS", "Complementary MOS", "Coupled MOS", "Complex MOS"], "answer": 1},
        {"q": "A MOSFET conducts when voltage is applied to?",
         "options": ["Source", "Drain", "Gate", "Body"], "answer": 2},
    ],
    "quantum-mechanics": [
        {"q": "What does superposition mean?",
         "options": ["Two particles collide", "Particle in multiple states", "Wave collapse", "Energy quantization"], "answer": 1},
        {"q": "Which principle limits knowing position AND momentum?",
         "options": ["Pauli exclusion", "Uncertainty", "Entanglement", "Complementarity"], "answer": 1},
        {"q": "Qubits differ from bits because they can be?",
         "options": ["Faster", "0, 1, or both", "Smaller", "Analog"], "answer": 1},
    ],
    "linear-algebra": [
        {"q": "What does matrix multiplication represent?",
         "options": ["Addition", "Composition of transformations", "Division", "Sorting"], "answer": 1},
        {"q": "Eigenvectors represent directions that are?",
         "options": ["Changed most", "Unchanged by transformation", "Random", "Orthogonal only"], "answer": 1},
        {"q": "SVD stands for?",
         "options": ["Simple Vector Decomposition", "Singular Value Decomposition", "Sequential Vector Diagram", "Standard Value Derivation"], "answer": 1},
    ],
    "computer-architecture": [
        {"q": "Which is faster — L1 cache or DRAM?",
         "options": ["DRAM", "L1 cache", "Same speed", "Depends"], "answer": 1},
        {"q": "Pipelining improves performance by?",
         "options": ["Reducing power", "Overlapping instruction stages", "More RAM", "Compression"], "answer": 1},
        {"q": "ARM is dominant in which market?",
         "options": ["Servers", "Mobile", "Supercomputers", "Mainframes"], "answer": 1},
    ],
    # Add more as you expand
}


def load_guestbook():
    entries = []
    if not os.path.exists(GUESTBOOK_FILE):
        return entries
    with open(GUESTBOOK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "|" in line:
                parts = line.split("|", 2)
                if len(parts) == 3:
                    entries.append({"timestamp": parts[0], "name": parts[1], "message": parts[2]})
    return entries


def save_guestbook_entry(name, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = name.replace("|", "/").replace("\n", " ")[:40]
    message = message.replace("|", "/").replace("\n", " ")[:280]
    with open(GUESTBOOK_FILE, "a", encoding="utf-8") as f:
        f.write(timestamp + "|" + name + "|" + message + "\n")

TOPICS = {
    # ════════════════════════════════════════════════════════════
    # COMPUTER SCIENCE
    # ════════════════════════════════════════════════════════════
    "algorithms": {
        "title": "Algorithms",
        "icon": "⚙️",
        "summary": "The recipes of computing — precise steps that turn input into output.",
        "content": """
        <p>An <strong>algorithm</strong> is a finite sequence of unambiguous instructions
        that takes some input, performs a series of well-defined operations, and produces
        a desired output. You can think of it as a recipe: given ingredients (data),
        follow the steps, and you get a meal (result). The recipe itself is not the food
        — it is the <em>method</em>. Two cooks can follow different recipes to make the
        same dish, and one recipe might be much faster, cheaper, or tastier than another.
        The same is true of algorithms: for any given problem, some solutions are
        elegant, some are wasteful, and some are catastrophically slow.</p>

        <p>Algorithms are older than computers. The word comes from the 9th-century
        Persian mathematician Muhammad ibn Musa al-Khwarizmi, whose work on arithmetic
        was translated into Latin as <em>Algoritmi de numero Indorum</em>. His systematic
        methods for multiplication, division, and solving equations influenced
        mathematics for centuries. Long before silicon, people were writing down
        procedures for finding square roots (the Babylonians), computing the greatest
        common divisor (Euclid, ~300 BC), and solving linear systems (Chinese "Nine
        Chapters," ~200 BC). What changed with computers is that we can now execute
        billions of steps per second — which means the <em>quality</em> of the algorithm
        matters enormously.</p>

        <h3>Why Algorithms Matter</h3>
        <p>Imagine two programs that sort a list of one million names. One is bubble
        sort — about 500 billion comparisons. The other is merge sort — about 20 million
        comparisons. On a modern CPU, bubble sort takes hours; merge sort finishes in a
        fraction of a second. Same problem, same computer, but a difference of four
        orders of magnitude. When engineers talk about "scaling," this is what they
        mean: not whether a program works, but whether it still works when the input
        grows by a thousand times.</p>

        <h3>Big-O Notation</h3>
        <p>Big-O describes how runtime or memory grows as input size <em>n</em>
        increases. It ignores constant factors and focuses on the <em>shape</em> of the
        growth curve.</p>
        <ul>
            <li><strong>O(1) — Constant:</strong> Work independent of input size.</li>
            <li><strong>O(log n) — Logarithmic:</strong> Halves the problem each step.</li>
            <li><strong>O(n) — Linear:</strong> Scales with input.</li>
            <li><strong>O(n log n):</strong> Efficient sorting.</li>
            <li><strong>O(n²) — Quadratic:</strong> Nested loops.</li>
            <li><strong>O(2ⁿ) — Exponential:</strong> Doubles each added element.</li>
            <li><strong>O(n!) — Factorial:</strong> All permutations.</li>
        </ul>
        <p>Modern CPUs do ~10⁹ operations per second. O(n log n) handles n=10⁷.
        O(n²) chokes at n=10⁴. O(2ⁿ) dies at n=30.</p>

        <h3>Example: Binary Search</h3>
        <pre><code>def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low &lt;= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] &lt; target:
            low = mid + 1
        else:
            high = mid - 1
    return -1</code></pre>

        <h3>Computational Complexity</h3>
        <ul>
            <li><strong>P:</strong> Solvable in polynomial time.</li>
            <li><strong>NP:</strong> Verifiable in polynomial time.</li>
            <li><strong>NP-complete:</strong> Hardest problems in NP.</li>
            <li><strong>NP-hard:</strong> At least as hard as NP-complete.</li>
        </ul>
        <p>The <strong>P vs NP</strong> problem is one of the seven Millennium Prize
        Problems. If P = NP, cryptography would collapse.</p>
        """
    },

    "data-structures": {
        "title": "Data Structures",
        "icon": "🗂️",
        "summary": "How we organize data in memory shapes what our programs can do.",
        "content": """
        <p>A <strong>data structure</strong> is a way of organizing and storing data so
        that specific operations — search, insert, delete, traverse — can be performed
        efficiently. Where an algorithm describes <em>how</em> to do something, a data
        structure describes <em>where</em> the data lives. Choosing the wrong data
        structure can make even the smartest algorithm useless.</p>

        <p>Think of a library. You could store books in a pile (unordered), arrange them
        alphabetically (sorted array), or use an index card catalog (hash table). Each
        arrangement supports different operations well. There is no universally "best"
        structure — only the right one for the problem at hand.</p>

        <h3>Linear Structures</h3>
        <ul>
            <li><strong>Array:</strong> Contiguous memory. O(1) index access, O(n)
            insert/delete in middle.</li>
            <li><strong>Dynamic Array:</strong> Auto-resizing. Amortized O(1) append.</li>
            <li><strong>Linked List:</strong> Nodes with pointers. O(1) insert at known
            position, O(n) random access.</li>
            <li><strong>Stack:</strong> LIFO — used in function calls, undo, DFS.</li>
            <li><strong>Queue:</strong> FIFO — used in scheduling, BFS.</li>
            <li><strong>Deque:</strong> Double-ended queue — insert/remove both ends.</li>
        </ul>

        <h3>Hash Tables</h3>
        <p>Store key-value pairs. Hash function maps keys to buckets. Average O(1)
        lookup, insert, delete. Collisions handled by chaining or open addressing. The
        foundation of Python dicts, database indexes, and caches.</p>

        <h3>Trees</h3>
        <ul>
            <li><strong>Binary Tree:</strong> Nodes with ≤ 2 children.</li>
            <li><strong>BST:</strong> Left &lt; node &lt; right. O(log n) balanced.</li>
            <li><strong>AVL / Red-Black:</strong> Self-balancing trees.</li>
            <li><strong>Heap:</strong> Priority queues in O(log n).</li>
            <li><strong>Trie:</strong> Prefix tree for autocomplete.</li>
            <li><strong>B-Tree:</strong> Database indexes.</li>
        </ul>

        <h3>Complexity Cheat Sheet</h3>
        <pre><code>Structure       Access   Search   Insert   Delete
Array           O(1)     O(n)     O(n)     O(n)
Linked List     O(n)     O(n)     O(1)     O(1)
Hash Table      —        O(1)     O(1)     O(1)
BST (balanced)  O(log n) O(log n) O(log n) O(log n)
Heap            O(1)min  —        O(log n) O(log n)</code></pre>

        <h3>Example: A Stack</h3>
        <pre><code>class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop() if self.items else None

    def peek(self):
        return self.items[-1] if self.items else None

    def is_empty(self):
        return len(self.items) == 0</code></pre>
        """
    },

    "ai-ml": {
        "title": "Artificial Intelligence & ML",
        "icon": "🤖",
        "summary": "Teaching machines to learn from data, reason about the world, and act.",
        "content": """
        <p><strong>Artificial Intelligence (AI)</strong> is the broad project of building
        machines that perform tasks we associate with human intelligence.
        <strong>Machine Learning (ML)</strong> is the dominant approach: instead of
        hand-coding rules, we build systems that learn patterns from data.</p>

        <p>Early AI (1950s–1980s) tried to encode knowledge explicitly. These
        rule-based systems worked for narrow domains but shattered on real-world
        messiness. Machine learning flipped the approach: give the system thousands of
        examples and let it discover the rules itself.</p>

        <h3>The AI Family Tree</h3>
        <ul>
            <li><strong>AI:</strong> Any technique enabling intelligent behavior.</li>
            <li><strong>ML:</strong> Systems that improve through data.</li>
            <li><strong>Deep Learning:</strong> Multi-layer neural networks.</li>
            <li><strong>Generative AI:</strong> Models that create content.</li>
        </ul>

        <h3>Three Paradigms</h3>
        <ul>
            <li><strong>Supervised:</strong> Learn from labeled data.</li>
            <li><strong>Unsupervised:</strong> Find structure in unlabeled data.</li>
            <li><strong>Reinforcement:</strong> Learn via rewards and penalties.</li>
        </ul>

        <h3>Core Concepts</h3>
        <ul>
            <li><strong>Features:</strong> Input variables.</li>
            <li><strong>Labels:</strong> Target outputs.</li>
            <li><strong>Train/Val/Test:</strong> Typically 70/15/15.</li>
            <li><strong>Loss function:</strong> Measures error.</li>
            <li><strong>Gradient descent:</strong> Adjusts weights to reduce loss.</li>
            <li><strong>Overfitting:</strong> Memorizes training data.</li>
        </ul>

        <h3>Classic Algorithms</h3>
        <ul>
            <li><strong>Linear Regression:</strong> Fits a line.</li>
            <li><strong>Logistic Regression:</strong> Binary classification.</li>
            <li><strong>Decision Trees / Random Forests:</strong> Tree-based.</li>
            <li><strong>Gradient Boosting:</strong> XGBoost, LightGBM.</li>
            <li><strong>SVMs:</strong> Max-margin classifiers.</li>
            <li><strong>K-Means:</strong> Clustering.</li>
            <li><strong>KNN:</strong> Nearest neighbors.</li>
        </ul>

        <h3>Deep Learning</h3>
        <ul>
            <li><strong>CNNs:</strong> Images.</li>
            <li><strong>RNNs / LSTMs:</strong> Sequences.</li>
            <li><strong>Transformers:</strong> Attention-based, powering GPT, BERT, Claude.</li>
            <li><strong>Diffusion:</strong> Image generation.</li>
        </ul>

        <h3>Example: Linear Regression</h3>
        <pre><code>from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = LinearRegression()
model.fit(X_train, y_train)
print(f"R2 = {model.score(X_test, y_test):.3f}")</code></pre>

        <h3>Ethics</h3>
        <ul>
            <li><strong>Bias:</strong> Models inherit data biases.</li>
            <li><strong>Interpretability:</strong> Black-box models.</li>
            <li><strong>Hallucinations:</strong> LLMs generate confident falsehoods.</li>
            <li><strong>Compute cost:</strong> Enormous energy consumption.</li>
        </ul>
        """
    },

    "operating-systems": {
        "title": "Operating Systems",
        "icon": "💻",
        "summary": "The invisible manager that runs your computer.",
        "content": """
        <p>An <strong>operating system (OS)</strong> is the software layer between
        applications and hardware. It schedules your programs, allocates memory,
        handles disk and network I/O, and enforces security.</p>

        <h3>Core Responsibilities</h3>
        <ul>
            <li><strong>Process Management:</strong> Create, schedule, terminate.</li>
            <li><strong>Memory Management:</strong> RAM, virtual memory, paging.</li>
            <li><strong>File Systems:</strong> Persistent storage.</li>
            <li><strong>I/O Management:</strong> Device drivers.</li>
            <li><strong>Security &amp; Isolation:</strong> Between users and processes.</li>
        </ul>

        <h3>Processes and Threads</h3>
        <ul>
            <li><strong>Process:</strong> Isolated running instance.</li>
            <li><strong>Thread:</strong> Lightweight, shares memory.</li>
            <li><strong>Mutex:</strong> Lock, only one holder.</li>
            <li><strong>Semaphore:</strong> Counter, up to N holders.</li>
            <li><strong>Deadlock:</strong> Threads wait forever.</li>
        </ul>

        <h3>CPU Scheduling</h3>
        <ul>
            <li><strong>FCFS:</strong> Arrival order.</li>
            <li><strong>SJF:</strong> Shortest job first.</li>
            <li><strong>Round Robin:</strong> Fixed time slices.</li>
            <li><strong>Priority:</strong> Higher priority, with aging.</li>
        </ul>

        <h3>Memory</h3>
        <ul>
            <li><strong>Virtual memory:</strong> Private address space per process.</li>
            <li><strong>Paging:</strong> 4 KB pages mapped to frames.</li>
            <li><strong>Page fault:</strong> Loaded from disk.</li>
            <li><strong>TLB:</strong> Translation cache.</li>
            <li><strong>Thrashing:</strong> Excessive paging.</li>
        </ul>

        <h3>File Systems</h3>
        <ul>
            <li><strong>ext4 (Linux):</strong> Journaling.</li>
            <li><strong>NTFS (Windows):</strong> Rich metadata.</li>
            <li><strong>APFS (macOS):</strong> Snapshots, COW.</li>
            <li><strong>ZFS:</strong> Checksums, RAID.</li>
        </ul>

        <h3>Example: Threads</h3>
        <pre><code>import threading

counter = 0
lock = threading.Lock()

def increment():
    global counter
    for _ in range(100000):
        with lock:
            counter += 1

threads = [threading.Thread(target=increment) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
print(counter)</code></pre>
        """
    },

    "networking": {
        "title": "Computer Networks",
        "icon": "🌐",
        "summary": "How billions of machines talk to each other.",
        "content": """
        <p>A <strong>computer network</strong> is a set of devices connected to exchange
        data. Networks range from two laptops on a home router to the global internet.</p>

        <p>The magic of networking is <em>abstraction</em>. When you type
        <code>https://google.com</code>, you don't think about voltages, MAC addresses,
        IP routing, or TCP handshakes. Each layer hides the complexity below it.</p>

        <h3>The OSI Model</h3>
        <ol>
            <li><strong>Physical:</strong> Bits on the wire.</li>
            <li><strong>Data Link:</strong> Frames (Ethernet, Wi-Fi).</li>
            <li><strong>Network:</strong> Routing (IP).</li>
            <li><strong>Transport:</strong> End-to-end (TCP, UDP).</li>
            <li><strong>Session:</strong> Manage connections.</li>
            <li><strong>Presentation:</strong> Encoding, encryption.</li>
            <li><strong>Application:</strong> HTTP, DNS, SMTP.</li>
        </ol>

        <h3>Key Protocols</h3>
        <ul>
            <li><strong>IP:</strong> Addressing and routing.</li>
            <li><strong>TCP:</strong> Reliable, ordered.</li>
            <li><strong>UDP:</strong> Fast, unreliable.</li>
            <li><strong>HTTP/HTTPS:</strong> The web.</li>
            <li><strong>DNS:</strong> Name → IP.</li>
            <li><strong>DHCP:</strong> Auto-assign IP.</li>
            <li><strong>BGP:</strong> Between autonomous systems.</li>
        </ul>

        <h3>The TCP Handshake</h3>
        <pre><code>Client → Server:  SYN
Server → Client:  SYN-ACK
Client → Server:  ACK
[connection established]</code></pre>

        <h3>Example: HTTP Request</h3>
        <pre><code>import requests
response = requests.get("https://api.github.com")
print(response.status_code)</code></pre>

        <h3>Modern Topics</h3>
        <ul>
            <li><strong>CDNs:</strong> Edge caching.</li>
            <li><strong>Load balancers:</strong> Distribute traffic.</li>
            <li><strong>5G:</strong> Low latency mobile.</li>
            <li><strong>Zero Trust:</strong> Never trust, verify.</li>
        </ul>
        """
    },

    "databases": {
        "title": "Databases",
        "icon": "🗄️",
        "summary": "How we store, query, and protect the world's data.",
        "content": """
        <p>A <strong>database</strong> is an organized collection of data. Almost every
        application relies on one — banks, social networks, hospitals.</p>

        <h3>Relational Databases (SQL)</h3>
        <p>Introduced by Edgar Codd in 1970. Data in tables, queries in SQL.</p>
        <ul>
            <li><strong>PostgreSQL:</strong> Feature-rich, standards-compliant.</li>
            <li><strong>MySQL / MariaDB:</strong> Web-friendly.</li>
            <li><strong>SQLite:</strong> Embedded, zero-config.</li>
        </ul>

        <h3>ACID</h3>
        <ul>
            <li><strong>Atomicity:</strong> All or nothing.</li>
            <li><strong>Consistency:</strong> Valid transitions.</li>
            <li><strong>Isolation:</strong> Concurrent transactions independent.</li>
            <li><strong>Durability:</strong> Survives crashes.</li>
        </ul>

        <h3>NoSQL</h3>
        <ul>
            <li><strong>Document (MongoDB):</strong> JSON-like.</li>
            <li><strong>Key-Value (Redis):</strong> Blazing fast.</li>
            <li><strong>Column (Cassandra):</strong> Write throughput.</li>
            <li><strong>Graph (Neo4j):</strong> Relationships first-class.</li>
            <li><strong>Time-Series (InfluxDB):</strong> Metrics, logs.</li>
        </ul>

        <h3>CAP Theorem</h3>
        <p>Choose two of Consistency, Availability, Partition tolerance. Since partitions
        happen, real systems choose CP or AP.</p>

        <h3>Example: SQL Query</h3>
        <pre><code>SELECT u.name, COUNT(o.id) AS order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id
ORDER BY order_count DESC
LIMIT 10;</code></pre>
        """
    },

    # ════════════════════════════════════════════════════════════
    # SEMICONDUCTORS
    # ════════════════════════════════════════════════════════════
    "semiconductors": {
        "title": "Semiconductors Overview",
        "icon": "🔬",
        "summary": "The physics and engineering that turned sand into civilization's brain.",
        "content": """
        <p>A <strong>semiconductor</strong> is a material whose electrical conductivity
        lies between that of a conductor and an insulator — and whose conductivity can be
        precisely <em>controlled</em>. Silicon, found in ordinary sand, is the most
        important.</p>

        <p>In 1947, Bardeen, Brattain, and Shockley invented the transistor at Bell Labs.
        In 1958, Kilby and Noyce independently invented the integrated circuit. Since
        then, transistor counts have grown from a handful to hundreds of billions.</p>

        <h3>Why They Matter</h3>
        <p>Conductors always conduct. Insulators never do. Semiconductors conduct
        <em>when we want them to</em> — exactly what a switch needs. From this single
        property flow computers, radios, solar panels, LEDs, and lasers.</p>

        <h3>Explore Subtopics</h3>
        <ul>
            <li><strong>Semiconductor Physics</strong> — bands, doping, P-N junctions.</li>
            <li><strong>Transistors</strong> — MOSFETs, BJTs, switches.</li>
            <li><strong>Chip Fabrication</strong> — lithography, cleanrooms.</li>
            <li><strong>Integrated Circuits</strong> — VLSI, SoCs, chiplets.</li>
            <li><strong>Beyond Silicon</strong> — GaN, SiC, graphene, photonics.</li>
        </ul>
        """
    },

    "semiconductor-physics": {
        "title": "Semiconductor Physics",
        "icon": "🌌",
        "summary": "Energy bands, doping, and the physics of the P-N junction.",
        "content": """
        <p>To understand semiconductors, you must first understand what happens to
        electrons inside a solid. In an isolated atom, electrons occupy discrete energy
        levels. When trillions of atoms are packed into a crystal, these levels smear
        into continuous <strong>energy bands</strong>.</p>

        <h3>Energy Bands</h3>
        <ul>
            <li><strong>Valence band:</strong> Highest energies where electrons are
            bound.</li>
            <li><strong>Conduction band:</strong> Energies where electrons are free.</li>
            <li><strong>Band gap:</strong> Energy difference, in eV.</li>
        </ul>

        <p>The band gap separates three classes of materials:</p>
        <ul>
            <li><strong>Conductors:</strong> Bands overlap. Copper.</li>
            <li><strong>Insulators:</strong> Gap &gt; 5 eV. Glass, rubber.</li>
            <li><strong>Semiconductors:</strong> Gap 0.7–1.5 eV. Silicon (1.12 eV),
            germanium (0.67 eV), GaAs (1.42 eV).</li>
        </ul>

        <h3>Doping</h3>
        <p>Silicon has 4 valence electrons. Introduce a foreign atom:</p>
        <ul>
            <li><strong>N-type (donor):</strong> Phosphorus, arsenic (5 e⁻). Free
            electron. Negative carriers.</li>
            <li><strong>P-type (acceptor):</strong> Boron, gallium (3 e⁻). Hole.
            Positive carriers.</li>
        </ul>
        <p>Doping levels: 1 atom in 10 million — yet transforms behavior.</p>

        <h3>The P-N Junction</h3>
        <p>P and N silicon create a <strong>depletion region</strong> where electrons
        and holes recombine. An internal field blocks further diffusion.</p>
        <ul>
            <li><strong>Forward bias (+ to P):</strong> Current flows.</li>
            <li><strong>Reverse bias (− to P):</strong> Almost no current.</li>
        </ul>
        <p>This one-way behavior is a <strong>diode</strong> — foundation of every
        transistor, LED, solar cell, and laser.</p>

        <h3>Temperature Effects</h3>
        <p>Semiconductors conduct more when hot (opposite of metals). Devices need
        careful thermal management.</p>

        <h3>Quantum Effects at Small Scales</h3>
        <ul>
            <li><strong>Quantum tunneling:</strong> Electrons "leak" through barriers.</li>
            <li><strong>Confinement:</strong> Behavior changes at atomic scales.</li>
            <li><strong>Discrete dopants:</strong> Single atoms matter.</li>
        </ul>
        """
    },

    "transistors": {
        "title": "Transistors",
        "icon": "🔀",
        "summary": "The switch that changed the world — MOSFETs, BJTs, and how they work.",
        "content": """
        <p>The <strong>transistor</strong> is arguably the most important invention of
        the 20th century. It's a device with three terminals where a small signal at one
        terminal controls a large current between the other two.</p>

        <p>Before transistors, electronics used vacuum tubes — glass bulbs that consumed
        lots of power and failed frequently. ENIAC (1945) used 17,468 tubes and weighed
        30 tons. A single transistor now does the work of one vacuum tube but is smaller
        than a virus.</p>

        <h3>1. BJT — Bipolar Junction Transistor</h3>
        <p>The original (Bell Labs, 1947). NPN or PNP.</p>
        <ul>
            <li><strong>Emitter:</strong> Emits carriers.</li>
            <li><strong>Base:</strong> Thin, lightly doped.</li>
            <li><strong>Collector:</strong> Collects carriers.</li>
        </ul>
        <p>Small base current controls large collector current. β typically 50–300.
        Current-controlled.</p>

        <h3>2. MOSFET — Metal-Oxide-Semiconductor FET</h3>
        <p>Dominant in modern chips. Four terminals:</p>
        <ul>
            <li><strong>Source &amp; Drain:</strong> Doped regions.</li>
            <li><strong>Gate:</strong> Separated by thin oxide.</li>
            <li><strong>Body:</strong> Substrate.</li>
        </ul>
        <p>Gate voltage forms a conducting channel. Voltage-controlled. Almost zero
        idle power — hence billions per chip.</p>

        <h3>NMOS, PMOS, CMOS</h3>
        <ul>
            <li><strong>NMOS:</strong> Conducts when gate high. Electrons.</li>
            <li><strong>PMOS:</strong> Conducts when gate low. Holes.</li>
            <li><strong>CMOS:</strong> Both. Fast, low-power. Basis of modern digital
            chips.</li>
        </ul>

        <h3>Scaling and Moore's Law</h3>
        <ul>
            <li><strong>FinFET (2011):</strong> Vertical fin channel.</li>
            <li><strong>GAA (2022+):</strong> Gate-all-around.</li>
            <li><strong>3D stacking:</strong> Vertical dies.</li>
            <li><strong>New materials:</strong> High-κ, germanium.</li>
        </ul>

        <h3>Analog Transistors</h3>
        <p>Beyond switching, transistors amplify. A common-source amplifier turns a
        small gate voltage into a large drain swing.</p>
        """
    },

    "chip-fabrication": {
        "title": "Chip Fabrication",
        "icon": "🏭",
        "summary": "How sand becomes a CPU — photolithography, etching, and cleanrooms.",
        "content": """
        <p>Making a modern chip is the most complex manufacturing process humans have
        ever devised. A leading-edge fab costs $20+ billion, and each wafer goes through
        <strong>1,000+ process steps</strong> over 2–3 months.</p>

        <h3>Step 1: Pure Silicon</h3>
        <p>Start with silica (SiO₂) — sand. Heat with carbon to get raw silicon (98%).
        Purify to <strong>electronic-grade</strong> (99.9999999%).</p>

        <h3>Step 2: The Ingot and Wafers</h3>
        <p>Melted silicon pulled into a single crystal via <strong>Czochralski
        process</strong> — up to 300 mm diameter. Sliced into wafers (~775 µm) and
        polished.</p>

        <h3>Step 3: Photolithography</h3>
        <ol>
            <li>Coat with photoresist.</li>
            <li>Expose through mask with UV (193 nm) or EUV (13.5 nm).</li>
            <li>Develop.</li>
            <li>Etch.</li>
            <li>Strip resist.</li>
        </ol>
        <p>60–80 metal layers mean the cycle repeats that many times.</p>

        <h3>Step 4: Doping and Deposition</h3>
        <ul>
            <li><strong>Ion implantation:</strong> Fire dopant atoms.</li>
            <li><strong>CVD / PVD:</strong> Add metal, oxide, dielectric.</li>
            <li><strong>CMP:</strong> Flatten each layer.</li>
        </ul>

        <h3>Step 5: Metallization</h3>
        <p>15+ copper layers, connected by vias. Lower layers finest, upper coarser.</p>

        <h3>Step 6: Testing and Dicing</h3>
        <p>Chips probed, working dies diced out, bad ones discarded.</p>

        <h3>Step 7: Packaging</h3>
        <p>Die mounted, wire-bonded or flip-chip, sealed. Provides protection and
        connections.</p>

        <h3>EUV Lithography</h3>
        <ul>
            <li>Fire 30 kW CO₂ laser at molten tin droplets 50,000×/second.</li>
            <li>Vaporize tin into plasma.</li>
            <li>Reflect off multilayer mirrors.</li>
            <li>Vacuum, nanometer precision.</li>
        </ul>
        <p>ASML NXE: ~$150M. High-NA EUV: ~$380M.</p>

        <h3>The Yield Problem</h3>
        <p>Defects kill dies. <strong>Yield</strong> = working/total. Leading-edge
        initial yields 30–50%; mature nodes 90%+.</p>
        """
    },

    "integrated-circuits": {
        "title": "Integrated Circuits",
        "icon": "🧩",
        "summary": "From a handful of transistors to billions — the rise of VLSI and SoCs.",
        "content": """
        <p>An <strong>integrated circuit (IC)</strong> is a complete electronic circuit
        fabricated on a single piece of silicon. Invented in 1958 by Kilby (TI) and Noyce
        (Fairchild).</p>

        <h3>Generations of Integration</h3>
        <ul>
            <li><strong>SSI (1960s):</strong> 1–100 transistors.</li>
            <li><strong>MSI (1970s):</strong> 100–10,000.</li>
            <li><strong>LSI (1980s):</strong> 10,000–100,000.</li>
            <li><strong>VLSI (1990s):</strong> 100,000–1,000,000.</li>
            <li><strong>ULSI / SoC (Modern):</strong> Billions.</li>
        </ul>

        <h3>The Intel 4004 (1971)</h3>
        <p>2,300 transistors, 740 kHz, 4-bit. The first microprocessor.</p>

        <h3>Modern Examples</h3>
        <ul>
            <li><strong>Apple M-series:</strong> ~20 billion transistors.</li>
            <li><strong>NVIDIA H100:</strong> 80 billion, AI tensor cores.</li>
            <li><strong>AMD EPYC:</strong> 100+ billion across chiplets.</li>
            <li><strong>Cerebras WSE-3:</strong> 4 trillion — largest chip ever.</li>
        </ul>

        <h3>Chip Categories</h3>
        <ul>
            <li><strong>Logic (CPU, GPU, ASIC):</strong> Highest density.</li>
            <li><strong>Memory (DRAM, NAND, SRAM):</strong> Density per bit.</li>
            <li><strong>Analog &amp; Mixed-Signal:</strong> Power, RF, sensors.</li>
            <li><strong>FPGA:</strong> Reconfigurable logic.</li>
        </ul>

        <h3>Design Flow</h3>
        <ol>
            <li>Specification</li>
            <li>RTL Design (Verilog/VHDL)</li>
            <li>Simulation &amp; Verification</li>
            <li>Synthesis</li>
            <li>Place &amp; Route</li>
            <li>Timing Analysis</li>
            <li>Tapeout ($1M–$10M+ masks)</li>
            <li>Fabrication &amp; Packaging</li>
            <li>Bring-up &amp; Validation</li>
        </ol>

        <h3>Chiplets and Advanced Packaging</h3>
        <p>Monolithic chips hit reticle-size and yield limits. Modern designs use
        <strong>chiplets</strong> — smaller dies packaged together. AMD Ryzen, Intel
        Meteor Lake, Apple M Ultra use this approach.</p>

        <h3>System-on-Chip (SoC)</h3>
        <p>A modern SoC contains CPU, GPU, NPU, memory controller, I/O, radios, power
        management, and security — all on one chip a few cm². This is what makes your
        phone possible.</p>
        """
    },

    "beyond-silicon": {
        "title": "Beyond Silicon",
        "icon": "🚀",
        "summary": "GaN, SiC, graphene, photonics — the materials shaping post-silicon electronics.",
        "content": """
        <p>Silicon has powered the information age, but it has limits. At ~3 nm, quantum
        tunneling and heat make further shrinking impractical. The future will be built
        from a mix of materials — each specialized for a specific job.</p>

        <h3>Why Not Just Silicon?</h3>
        <ul>
            <li>Band gap 1.12 eV — limits temperature and voltage.</li>
            <li>Moderate electron mobility — limits speed.</li>
            <li>Poor thermal conductivity — heat bottleneck.</li>
            <li>Quantum tunneling — leakage.</li>
        </ul>

        <h3>Gallium Arsenide (GaAs)</h3>
        <ul>
            <li>Band gap 1.42 eV — emits light efficiently.</li>
            <li>Electron mobility ~6× silicon.</li>
            <li>LEDs, laser diodes, RF, radar, satellite comms.</li>
        </ul>

        <h3>Gallium Nitride (GaN)</h3>
        <ul>
            <li>Band gap 3.4 eV.</li>
            <li>Breakdown voltage ~10× silicon.</li>
            <li>Fast chargers, 5G base stations, radar.</li>
        </ul>

        <h3>Silicon Carbide (SiC)</h3>
        <ul>
            <li>Band gap 3.26 eV.</li>
            <li>Thermal conductivity 3× silicon.</li>
            <li>EV inverters, solar inverters, grid.</li>
        </ul>

        <h3>Graphene and 2D Materials</h3>
        <ul>
            <li><strong>Graphene:</strong> Single carbon layer. Extraordinary
            conductivity.</li>
            <li><strong>Problem:</strong> No band gap in pristine form.</li>
            <li><strong>MoS₂, WS₂:</strong> 2D semiconductors with band gaps.</li>
        </ul>

        <h3>Photonic Chips</h3>
        <p>Use photons instead of electrons. Data center interconnects, telecom, LIDAR,
        quantum.</p>

        <h3>Spintronics</h3>
        <p>Use electron spin. MRAM already ships — non-volatile, radiation-hard.</p>

        <h3>Quantum Computing Materials</h3>
        <ul>
            <li><strong>Superconducting qubits:</strong> Aluminum, niobium.</li>
            <li><strong>Trapped ions:</strong> Ytterbium, barium.</li>
            <li><strong>Topological qubits:</strong> Majorana fermions.</li>
            <li><strong>Photonic qubits:</strong> Single photons.</li>
        </ul>

        <h3>Neuromorphic Computing</h3>
        <p>Brain-inspired hardware — neurons and synapses. Energy-efficient for edge AI.
        Intel Loihi, IBM NorthPole.</p>

        <h3>Carbon Nanotubes</h3>
        <p>Rolled graphene cylinders. Conduct better than copper, stronger than steel.
        Manufacturing challenges remain.</p>

        <h3>The Post-Silicon Future</h3>
        <ul>
            <li>GaN and SiC for power.</li>
            <li>GaAs and InP for optical.</li>
            <li>Graphene and 2D for ultra-fast.</li>
            <li>Photonic for interconnects.</li>
            <li>Quantum for specific algorithms.</li>
        </ul>
        <p>The future is <em>heterogeneous</em> — many materials cooperating.</p>
        """
    },

    # ════════════════════════════════════════════════════════════
    # ELECTRICAL ENGINEERING
    # ════════════════════════════════════════════════════════════
    "electrical-engineering": {
        "title": "Electrical Engineering Overview",
        "icon": "⚡",
        "summary": "The study of electricity — circuits, signals, power, and control.",
        "content": """
        <p><strong>Electrical Engineering (EE)</strong> is the discipline concerned with
        the design, analysis, and application of systems involving electricity.</p>

        <p>Computer science is often taught separately from EE, but they share deep
        roots. The first computers were built by electrical engineers. Modern CPUs are
        EE-designed circuits.</p>

        <h3>Explore Subtopics</h3>
        <ul>
            <li><strong>Circuit Analysis</strong> — Ohm's law, Kirchhoff.</li>
            <li><strong>Digital Logic</strong> — gates, flip-flops, FSMs.</li>
            <li><strong>Signals &amp; Systems</strong> — Fourier, filters.</li>
            <li><strong>Power Systems</strong> — generation, grid, renewables.</li>
            <li><strong>Control Systems</strong> — feedback, PID.</li>
        </ul>

        <h3>Fundamental Quantities</h3>
        <ul>
            <li><strong>Voltage (V):</strong> Potential difference.</li>
            <li><strong>Current (I):</strong> Charge flow rate.</li>
            <li><strong>Resistance (R):</strong> Opposition to current.</li>
            <li><strong>Power (P):</strong> Energy transfer rate.</li>
            <li><strong>Capacitance (C):</strong> Stores charge.</li>
            <li><strong>Inductance (L):</strong> Stores magnetic energy.</li>
        </ul>

        <h3>Ohm's Law</h3>
        <pre><code>V = I × R
P = V × I = I² × R = V² / R</code></pre>
        """
    },

    "circuit-analysis": {
        "title": "Circuit Analysis",
        "icon": "🔌",
        "summary": "Ohm's law, Kirchhoff's laws, and the tools for solving circuits.",
        "content": """
        <p><strong>Circuit analysis</strong> is the systematic study of voltage and
        current in electrical networks. It's applied mathematics — write equations based
        on physical laws, then solve them.</p>

        <h3>Voltage, Current, Resistance</h3>
        <ul>
            <li><strong>Voltage:</strong> Pressure. Measured across.</li>
            <li><strong>Current:</strong> Flow. Measured through.</li>
            <li><strong>Resistance:</strong> Opposition. Ohms.</li>
        </ul>

        <h3>Ohm's Law</h3>
        <pre><code>V = I × R</code></pre>

        <h3>Power</h3>
        <pre><code>P = V × I = I² × R = V² / R</code></pre>
        <p>Every resistor converts electrical energy to heat.</p>

        <h3>Series and Parallel</h3>
        <ul>
            <li><strong>Series:</strong> Same current. R = R1 + R2 + ...</li>
            <li><strong>Parallel:</strong> Same voltage. 1/R = 1/R1 + 1/R2 + ...</li>
        </ul>

        <h3>Kirchhoff's Laws</h3>
        <ul>
            <li><strong>KCL:</strong> Sum of currents into node = sum out.</li>
            <li><strong>KVL:</strong> Sum of voltages around loop = 0.</li>
        </ul>

        <h3>Node Voltage Method</h3>
        <p>Pick a ground. Assign unknowns to every other node. Apply KCL. Solve.</p>
        <pre><code>Node 1: (V1 - V2)/R2 + (V1 - V3)/R3 = I_source
Node 2: (V2 - V1)/R2 + V2/R4 = 0
Node 3: (V3 - V1)/R3 + V3/R5 = 0</code></pre>

        <h3>Mesh Current Method</h3>
        <p>Assign loop currents. Apply KVL. Solve.</p>

        <h3>Thevenin and Norton</h3>
        <ul>
            <li><strong>Thevenin:</strong> V_th in series with R_th.</li>
            <li><strong>Norton:</strong> I_n in parallel with R_n.</li>
        </ul>

        <h3>Superposition</h3>
        <p>Response = sum of responses to each source acting alone.</p>

        <h3>Example: Voltage Divider</h3>
        <pre><code>Vout = Vin × R2 / (R1 + R2)</code></pre>

        <h3>Example: RC Transient</h3>
        <pre><code>V_C(t) = V_in × (1 - e^(-t/RC))
Time constant τ = RC</code></pre>

        <h3>AC Analysis</h3>
        <pre><code>Z_R = R
Z_C = 1 / (jωC)
Z_L = jωL
ω = 2πf</code></pre>

        <h3>Simulation</h3>
        <p>SPICE solves circuit equations numerically. Free: LTspice, ngspice.
        Commercial: Cadence, Synopsys.</p>
        """
    },

    "digital-logic": {
        "title": "Digital Logic",
        "icon": "🔢",
        "summary": "Gates, flip-flops, and how abstract 1s and 0s become computers.",
        "content": """
        <p><strong>Digital logic</strong> is the bridge between physics and computation.
        It turns the analog world of continuous voltages into a clean, discrete world of
        0s and 1s.</p>

        <h3>Binary and Boolean Algebra</h3>
        <ul>
            <li><strong>Logic 0:</strong> Low voltage.</li>
            <li><strong>Logic 1:</strong> High voltage.</li>
        </ul>

        <h3>Basic Gates</h3>
        <ul>
            <li><strong>AND:</strong> 1 if all inputs 1.</li>
            <li><strong>OR:</strong> 1 if any input 1.</li>
            <li><strong>NOT:</strong> Inverts.</li>
            <li><strong>NAND:</strong> Universal.</li>
            <li><strong>NOR:</strong> Universal.</li>
            <li><strong>XOR:</strong> 1 if inputs differ.</li>
            <li><strong>XNOR:</strong> 1 if inputs match.</li>
        </ul>

        <h3>Truth Tables</h3>
        <pre><code>A  B  | AND  OR  NAND  NOR  XOR  XNOR
0  0  |  0    0     1     1    0     1
0  1  |  0    1     1     0    1     0
1  0  |  0    1     1     0    1     0
1  1  |  1    1     0     0    0     1</code></pre>

        <h3>Combinational Circuits</h3>
        <ul>
            <li><strong>Half adder:</strong> Sum + carry of two bits.</li>
            <li><strong>Full adder:</strong> Handles carry-in.</li>
            <li><strong>Multiplexer (MUX):</strong> Selects one input.</li>
            <li><strong>Decoder:</strong> n → 2ⁿ outputs.</li>
            <li><strong>ALU:</strong> Arithmetic Logic Unit.</li>
        </ul>

        <h3>Sequential Circuits</h3>
        <ul>
            <li><strong>D Flip-Flop:</strong> Captures input on clock edge.</li>
            <li><strong>Registers:</strong> Groups of flip-flops.</li>
            <li><strong>Counters:</strong> Sequence through states.</li>
            <li><strong>FSM:</strong> States + transitions.</li>
        </ul>

        <h3>Clocking and Timing</h3>
        <p>Setup time, hold time, metastability. Clock speed limited by critical
        path.</p>

        <h3>From Gates to CPUs</h3>
        <p>ALU + registers + control + memory interface = a CPU.</p>

        <h3>Hardware Description Languages</h3>
        <pre><code>module adder(input [7:0] a, b, output [7:0] sum);
    assign sum = a + b;
endmodule</code></pre>

        <h3>FPGAs and ASICs</h3>
        <ul>
            <li><strong>FPGA:</strong> Reconfigurable.</li>
            <li><strong>ASIC:</strong> Custom, fast, expensive.</li>
        </ul>
        """
    },

    "signals-systems": {
        "title": "Signals & Systems",
        "icon": "📡",
        "summary": "Fourier, filters, sampling, and how information rides on waves.",
        "content": """
        <p><strong>Signals</strong> are functions that carry information.
        <strong>Systems</strong> transform signals. Signals and Systems is the
        mathematical backbone of communications, audio, control, and imaging.</p>

        <h3>Types of Signals</h3>
        <ul>
            <li><strong>Continuous-time (analog):</strong> Sound, temperature.</li>
            <li><strong>Discrete-time:</strong> Digital audio, sampled sensors.</li>
            <li><strong>Periodic:</strong> Repeats.</li>
            <li><strong>Aperiodic:</strong> Doesn't repeat.</li>
        </ul>

        <h3>Sinusoids</h3>
        <pre><code>x(t) = A × sin(2πft + φ)</code></pre>
        <p>Sinusoids are the building blocks — linear systems preserve them.</p>

        <h3>Fourier</h3>
        <ul>
            <li><strong>Fourier Series:</strong> Periodic signals = sum of sinusoids.</li>
            <li><strong>Fourier Transform:</strong> Any signal = integral of sinusoids.</li>
            <li><strong>FFT:</strong> Fast algorithm, O(n log n).</li>
        </ul>

        <h3>Sampling</h3>
        <ul>
            <li><strong>Nyquist:</strong> Sample at ≥ 2× highest frequency.</li>
            <li><strong>Aliasing:</strong> Under-sampling causes artifacts.</li>
            <li><strong>Quantization:</strong> Rounding to levels.</li>
            <li><strong>Dithering:</strong> Adding noise to reduce artifacts.</li>
        </ul>

        <h3>Filters</h3>
        <ul>
            <li><strong>Low-pass:</strong> Smoothing.</li>
            <li><strong>High-pass:</strong> Removes DC.</li>
            <li><strong>Band-pass:</strong> Radio tuning.</li>
            <li><strong>Notch:</strong> Removes 60 Hz hum.</li>
        </ul>

        <h3>Modulation</h3>
        <ul>
            <li><strong>AM:</strong> Vary amplitude.</li>
            <li><strong>FM:</strong> Vary frequency.</li>
            <li><strong>QAM:</strong> Amplitude + phase. Wi-Fi, cable, 5G.</li>
            <li><strong>OFDM:</strong> Many subcarriers.</li>
            <li><strong>Spread spectrum:</strong> GPS, Bluetooth, Wi-Fi.</li>
        </ul>

        <h3>Example: RC Low-Pass Filter</h3>
        <pre><code>Cutoff: f_c = 1 / (2πRC)</code></pre>

        <h3>Applications</h3>
        <ul>
            <li><strong>Audio:</strong> Equalizers, compression.</li>
            <li><strong>Imaging:</strong> JPEG uses DCT.</li>
            <li><strong>Communications:</strong> Modems, Wi-Fi.</li>
            <li><strong>Medical:</strong> ECG, EEG, ultrasound.</li>
        </ul>
        """
    },

    "power-systems": {
        "title": "Power Systems",
        "icon": "🔋",
        "summary": "Generation, transmission, and the electrical grid.",
        "content": """
        <p><strong>Power systems</strong> are the vast networks that generate,
        transmit, and distribute electrical energy. They're the largest machines ever
        built by humans.</p>

        <p>The grid must match generation to demand instantaneously. If balance is lost,
        frequency drifts and cascading failures can black out entire regions (2003
        Northeast blackout: 55 million people).</p>

        <h3>Generation</h3>
        <ul>
            <li><strong>Thermal:</strong> Heat → steam → turbine.</li>
            <li><strong>Nuclear:</strong> Carbon-free, radioactive waste.</li>
            <li><strong>Hydro:</strong> Falling water.</li>
            <li><strong>Wind:</strong> Variable output.</li>
            <li><strong>Solar PV:</strong> Photons → electrons.</li>
            <li><strong>Geothermal:</strong> Earth's heat.</li>
        </ul>

        <h3>Transmission</h3>
        <ul>
            <li><strong>High-voltage AC:</strong> 100–800 kV. Reduces losses.</li>
            <li><strong>HVDC:</strong> Long lines, undersea cables.</li>
            <li><strong>Transformers:</strong> Step voltage up/down.</li>
        </ul>

        <h3>Distribution</h3>
        <ul>
            <li><strong>Substations:</strong> Step down (e.g., 13.8 kV).</li>
            <li><strong>Service transformers:</strong> 120/240V for homes.</li>
            <li><strong>Smart meters:</strong> Demand response.</li>
        </ul>

        <h3>Grid Stability</h3>
        <ul>
            <li><strong>Frequency:</strong> 50 or 60 Hz — barometer of balance.</li>
            <li><strong>Inertia:</strong> Rotating generators provide stability.</li>
            <li><strong>Reserves:</strong> Fast-responding generation.</li>
            <li><strong>Load shedding:</strong> Controlled blackouts to prevent
            collapse.</li>
        </ul>

        <h3>Renewables and Storage</h3>
        <ul>
            <li><strong>Solar:</strong> Peak midday.</li>
            <li><strong>Wind:</strong> Variable.</li>
            <li><strong>Battery:</strong> Grid-scale Li-ion, flow batteries.</li>
            <li><strong>Pumped hydro:</strong> 80% round-trip efficiency.</li>
            <li><strong>Hydrogen:</strong> Long-duration storage.</li>
        </ul>

        <h3>Smart Grid</h3>
        <ul>
            <li><strong>AMI:</strong> Automatic meter reading.</li>
            <li><strong>Demand response:</strong> Adjust loads.</li>
            <li><strong>Microgrids:</strong> Local generation + storage.</li>
            <li><strong>V2G:</strong> EV batteries help stabilize.</li>
        </ul>

        <h3>Challenges</h3>
        <ul>
            <li><strong>Decarbonization.</strong></li>
            <li><strong>Aging infrastructure.</strong></li>
            <li><strong>Cyber security.</strong></li>
            <li><strong>Equity.</strong></li>
            <li><strong>Extreme weather.</strong></li>
        </ul>
        """
    },

    "control-systems": {
        "title": "Control Systems",
        "icon": "🎛️",
        "summary": "Feedback, PID, stability — how machines regulate themselves.",
        "content": """
        <p><strong>Control systems</strong> keep variables at desired values — speed,
        temperature, position, voltage — despite disturbances. From thermostats to
        fighter jets, they're everywhere.</p>

        <h3>Open-Loop vs Closed-Loop</h3>
        <ul>
            <li><strong>Open-loop:</strong> No feedback. Simple, can't correct.</li>
            <li><strong>Closed-loop:</strong> Measure, compare, adjust. Corrects errors.</li>
        </ul>

        <h3>Feedback Components</h3>
        <ul>
            <li><strong>Setpoint:</strong> Desired value.</li>
            <li><strong>Sensor:</strong> Measures actual.</li>
            <li><strong>Error:</strong> Setpoint − measured.</li>
            <li><strong>Controller:</strong> Decides action.</li>
            <li><strong>Actuator:</strong> Applies action.</li>
            <li><strong>Plant:</strong> System being controlled.</li>
        </ul>

        <h3>PID Control</h3>
        <pre><code>u(t) = Kp×e(t) + Ki×∫e(τ)dτ + Kd×de(t)/dt</code></pre>
        <ul>
            <li><strong>Kp:</strong> Proportional — current error.</li>
            <li><strong>Ki:</strong> Integral — eliminates offset.</li>
            <li><strong>Kd:</strong> Derivative — damps oscillation.</li>
        </ul>

        <h3>Tuning</h3>
        <ul>
            <li><strong>Too much Kp:</strong> Overshoot, oscillation.</li>
            <li><strong>Too much Ki:</strong> Slow oscillation, windup.</li>
            <li><strong>Too much Kd:</strong> Noise, jitter.</li>
            <li><strong>Ziegler-Nichols:</strong> Classic tuning rules.</li>
        </ul>

        <h3>Stability</h3>
        <ul>
            <li><strong>Poles and zeros.</strong></li>
            <li><strong>Routh-Hurwitz.</strong></li>
            <li><strong>Nyquist.</strong></li>
            <li><strong>Bode plots.</strong></li>
            <li><strong>Root locus.</strong></li>
        </ul>

        <h3>Beyond PID</h3>
        <ul>
            <li><strong>State-space control:</strong> LQR, pole placement.</li>
            <li><strong>MPC:</strong> Predictive, optimal.</li>
            <li><strong>Adaptive:</strong> Adjusts to changes.</li>
            <li><strong>Robust:</strong> Handles uncertainty.</li>
            <li><strong>Fuzzy:</strong> Rule-based.</li>
            <li><strong>Neural network control:</strong> Learned.</li>
        </ul>

        <h3>Example: Cruise Control</h3>
        <ul>
            <li>Setpoint: 65 mph.</li>
            <li>Sensor: wheel speed.</li>
            <li>Controller: PID.</li>
            <li>Actuator: throttle.</li>
            <li>Plant: car.</li>
            <li>Disturbance: hills, wind.</li>
        </ul>

        <h3>Applications</h3>
        <ul>
            <li><strong>Aerospace:</strong> Autopilots, missiles.</li>
            <li><strong>Robotics:</strong> Joint control, balance.</li>
            <li><strong>Automotive:</strong> Engine, ABS, cruise.</li>
            <li><strong>Industrial:</strong> Temperature, pressure, flow.</li>
            <li><strong>Consumer:</strong> Thermostats, drones.</li>
            <li><strong>Medical:</strong> Insulin pumps, ventilators.</li>
        </ul>
        """
    },

    # ════════════════════════════════════════════════════════════
    # MATHEMATICS
    # ════════════════════════════════════════════════════════════
    "linear-algebra": {
        "title": "Linear Algebra",
        "icon": "📐",
        "summary": "Vectors, matrices, and the mathematics behind transformations and data.",
        "content": """
        <p><strong>Linear algebra</strong> is the study of vectors, matrices, and the
        linear transformations between them. It's arguably the most-used branch of
        mathematics in computing — from graphics and machine learning to quantum
        mechanics and search engines.</p>

        <h3>Why It Matters</h3>
        <p>Whenever you have many numbers that interact with each other — pixels in an
        image, features in a dataset, positions in 3D space, probabilities in a model —
        linear algebra gives you the vocabulary to reason about them.</p>

        <h3>Core Concepts</h3>
        <ul>
            <li><strong>Vectors:</strong> Ordered lists of numbers. Represent points,
            directions, or data.</li>
            <li><strong>Matrices:</strong> 2D grids of numbers. Represent linear
            transformations or systems of equations.</li>
            <li><strong>Matrix multiplication:</strong> Composition of transformations.</li>
            <li><strong>Determinant:</strong> Measures volume change.</li>
            <li><strong>Eigenvalues and eigenvectors:</strong> Directions unchanged by a
            transformation. Used in PCA, PageRank, and stability analysis.</li>
            <li><strong>Rank, null space, column space:</strong> Fundamental subspaces
            associated with any matrix.</li>
            <li><strong>Singular Value Decomposition (SVD):</strong> Factor a matrix into
            three useful pieces. The backbone of compression and recommendation.</li>
        </ul>

        <h3>Example: Matrix Multiplication</h3>
        <pre><code>import numpy as np

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

C = A @ B   # matrix product
print(C)
# [[19 22]
#  [43 50]]</code></pre>

        <h3>Applications</h3>
        <ul>
            <li><strong>Graphics:</strong> Every rotation, scaling, and projection is a
            matrix.</li>
            <li><strong>Machine learning:</strong> Neural networks are compositions of
            matrix multiplications.</li>
            <li><strong>Search engines:</strong> Google's PageRank is an eigenvector of
            the web graph.</li>
            <li><strong>Physics:</strong> Quantum states are vectors in Hilbert space;
            observables are operators.</li>
            <li><strong>Data science:</strong> PCA and SVD reveal structure in high-
            dimensional data.</li>
        </ul>
        """
    },

    "calculus": {
        "title": "Calculus",
        "icon": "∫",
        "summary": "Rates of change and accumulation — the mathematics of continuous processes.",
        "content": """
        <p><strong>Calculus</strong> deals with change and accumulation. It was invented
        independently by Newton and Leibniz in the 17th century, and it remains the
        language of physics, engineering, and optimization.</p>

        <h3>Two Great Ideas</h3>
        <ul>
            <li><strong>Differentiation:</strong> How fast is something changing? The
            derivative gives the slope of a curve at any point.</li>
            <li><strong>Integration:</strong> How much has accumulated? The integral
            gives the area under a curve.</li>
        </ul>

        <h3>Core Concepts</h3>
        <ul>
            <li><strong>Limits:</strong> The foundation — what happens as a value
            approaches another.</li>
            <li><strong>Derivative:</strong> Rate of change. f'(x) = lim (f(x+h) − f(x))/h.</li>
            <li><strong>Chain rule:</strong> The derivative of a composition.</li>
            <li><strong>Integral:</strong> Anti-derivative; area under a curve.</li>
            <li><strong>Fundamental theorem:</strong> Differentiation and integration are
            inverse operations.</li>
            <li><strong>Multivariable calculus:</strong> Gradients, partial derivatives,
            divergence, curl.</li>
        </ul>

        <h3>Why CS Cares</h3>
        <p>Gradient descent — the algorithm at the heart of machine learning — uses
        derivatives to find the direction of steepest descent. Every neural network
        training loop runs on the chain rule applied at massive scale (automatic
        differentiation).</p>

        <h3>Example: Gradient of a Function</h3>
        <pre><code>import numpy as np

def f(x):       # f(x) = x^2 + 3x
    return x**2 + 3*x

def f_prime(x): # derivative: 2x + 3
    return 2*x + 3

print(f(5))         # 40
print(f_prime(5))   # 13</code></pre>

        <h3>Applications</h3>
        <ul>
            <li><strong>Optimization:</strong> Finding minima and maxima.</li>
            <li><strong>Physics:</strong> Motion, forces, fields.</li>
            <li><strong>Machine learning:</strong> Gradient descent, backpropagation.</li>
            <li><strong>Graphics:</strong> Smooth interpolation, surface normals.</li>
            <li><strong>Economics:</strong> Marginal analysis, growth rates.</li>
        </ul>
        """
    },

    "discrete-math": {
        "title": "Discrete Mathematics",
        "icon": "🔷",
        "summary": "Logic, sets, graphs, and combinatorics — the mathematics of computer science.",
        "content": """
        <p><strong>Discrete mathematics</strong> studies objects that take distinct,
        separated values — integers, graphs, logical propositions, finite sets. It's the
        mathematical foundation of computer science, more so than calculus.</p>

        <h3>Major Areas</h3>
        <ul>
            <li><strong>Logic:</strong> Propositional and predicate logic. The basis of
            proof and digital circuits.</li>
            <li><strong>Set theory:</strong> Collections, unions, intersections,
            functions, relations.</li>
            <li><strong>Combinatorics:</strong> Counting, permutations, combinations,
            pigeonhole principle.</li>
            <li><strong>Graph theory:</strong> Vertices, edges, paths, cycles, coloring,
            spanning trees.</li>
            <li><strong>Number theory:</strong> Primes, modular arithmetic, RSA
            cryptography.</li>
            <li><strong>Recursion and induction:</strong> Proof techniques that mirror
            recursive algorithms.</li>
        </ul>

        <h3>Why CS Cares</h3>
        <p>Computer science deals with discrete objects: integers, strings, trees,
        graphs. Continuous math (calculus) rarely applies directly. Discrete math gives
        you the tools to reason about algorithms, prove correctness, analyze complexity,
        and design databases.</p>

        <h3>Example: Proof by Induction</h3>
        <pre><code>Claim: 1 + 2 + ... + n = n(n+1)/2

Base case: n = 1 → 1 = 1(2)/2 = 1 ✓

Inductive step:
  Assume true for n.
  Show true for n+1:
  1 + 2 + ... + n + (n+1)
  = n(n+1)/2 + (n+1)
  = (n+1)(n+2)/2 ✓

Therefore true for all n ≥ 1.</code></pre>

        <h3>Applications</h3>
        <ul>
            <li><strong>Algorithms:</strong> Complexity analysis, correctness proofs.</li>
            <li><strong>Cryptography:</strong> Number theory, modular arithmetic.</li>
            <li><strong>Databases:</strong> Relational algebra, query optimization.</li>
            <li><strong>Compilers:</strong> Automata theory, formal grammars.</li>
            <li><strong>Networks:</strong> Graph algorithms, routing.</li>
        </ul>
        """
    },

    "probability": {
        "title": "Probability & Statistics",
        "icon": "🎲",
        "summary": "Reasoning under uncertainty — random variables, distributions, and inference.",
        "content": """
        <p><strong>Probability</strong> quantifies uncertainty.
        <strong>Statistics</strong> extracts knowledge from data. Together, they're the
        mathematical foundation of machine learning, data science, and quantitative
        reasoning.</p>

        <h3>Probability Basics</h3>
        <ul>
            <li><strong>Sample space:</strong> All possible outcomes.</li>
            <li><strong>Events:</strong> Subsets of the sample space.</li>
            <li><strong>Axioms:</strong> Non-negative, sum to 1, additivity for
            disjoint events.</li>
            <li><strong>Conditional probability:</strong> P(A|B) = P(A∩B)/P(B).</li>
            <li><strong>Bayes' theorem:</strong> Updating beliefs with new evidence.</li>
            <li><strong>Independence:</strong> P(A∩B) = P(A)·P(B).</li>
        </ul>

        <h3>Random Variables</h3>
        <ul>
            <li><strong>Discrete:</strong> Bernoulli, Binomial, Poisson, Geometric.</li>
            <li><strong>Continuous:</strong> Uniform, Normal (Gaussian), Exponential,
            Beta.</li>
            <li><strong>Expected value:</strong> Long-run average.</li>
            <li><strong>Variance:</strong> Spread around the mean.</li>
        </ul>

        <h3>Statistics</h3>
        <ul>
            <li><strong>Descriptive:</strong> Mean, median, mode, variance, percentiles.</li>
            <li><strong>Inferential:</strong> Estimation, hypothesis testing, confidence
            intervals.</li>
            <li><strong>Bayesian:</strong> Priors, likelihoods, posteriors.</li>
            <li><strong>Regression:</strong> Modeling relationships between variables.</li>
        </ul>

        <h3>Example: Bayes' Theorem</h3>
        <pre><code>P(disease | positive test)
  = P(positive | disease) · P(disease)
    ─────────────────────────────────────
           P(positive test)

Even with a 99% accurate test, a rare disease
can produce mostly false positives.</code></pre>

        <h3>Applications</h3>
        <ul>
            <li><strong>Machine learning:</strong> Naive Bayes, probabilistic graphical
            models.</li>
            <li><strong>Data science:</strong> A/B testing, confidence intervals.</li>
            <li><strong>Finance:</strong> Risk models, option pricing (Black-Scholes).</li>
            <li><strong>Medicine:</strong> Diagnostic testing, clinical trials.</li>
            <li><strong>Games:</strong> AI opponent modeling, random generation.</li>
        </ul>
        """
    },

    "number-theory": {
        "title": "Number Theory",
        "icon": "🔢",
        "summary": "The properties of integers — primes, divisibility, and modular arithmetic.",
        "content": """
        <p><strong>Number theory</strong> is the study of integers — their properties,
        relationships, and patterns. Once considered the purest (most "useless") branch
        of mathematics, it's now the foundation of modern cryptography.</p>

        <h3>Core Concepts</h3>
        <ul>
            <li><strong>Divisibility:</strong> When does a divide b? gcd, lcm, Euclidean
            algorithm.</li>
            <li><strong>Primes:</strong> Numbers with no divisors except 1 and themselves.
            The atoms of arithmetic.</li>
            <li><strong>Fundamental theorem of arithmetic:</strong> Every integer factors
            uniquely into primes.</li>
            <li><strong>Modular arithmetic:</strong> Clock arithmetic. a ≡ b (mod n).</li>
            <li><strong>Fermat's little theorem:</strong> a^(p−1) ≡ 1 (mod p) for prime
            p.</li>
            <li><strong>Euler's totient:</strong> Counts numbers coprime to n.</li>
            <li><strong>Chinese remainder theorem:</strong> Solve systems of congruences.</li>
        </ul>

        <h3>Why CS Cares</h3>
        <p>Modern cryptography — RSA, Diffie-Hellman, elliptic curves — is built on
        number theory. Every time you visit an HTTPS website, number-theoretic
        algorithms are running behind the scenes to keep your connection secure.</p>

        <h3>Example: RSA Encryption (simplified)</h3>
        <pre><code># Choose two large primes
p, q = 61, 53
n = p * q             # 3233
phi = (p-1) * (q-1)   # 3120

# Choose e coprime to phi
e = 17

# d = e^(-1) mod phi
d = pow(e, -1, phi)   # 2753

# Public key: (n, e) = (3233, 17)
# Private key: d = 2753

# Encrypt m=65: c = m^e mod n = 2790
# Decrypt: m = c^d mod n = 65</code></pre>

        <h3>Applications</h3>
        <ul>
            <li><strong>Cryptography:</strong> RSA, DH, ECC.</li>
            <li><strong>Hashing:</strong> Prime-based hash functions.</li>
            <li><strong>Random number generation:</strong> Prime sieves and modular
            arithmetic.</li>
            <li><strong>Error-correcting codes:</strong> Reed-Solomon uses finite
            fields.</li>
            <li><strong>Competitive programming:</strong> Fast modular exponentiation,
            prime testing.</li>
        </ul>
        """
    },

    # ════════════════════════════════════════════════════════════
    # COMPUTER ENGINEERING
    # ════════════════════════════════════════════════════════════
    "computer-architecture": {
        "title": "Computer Architecture",
        "icon": "🏛️",
        "summary": "How CPUs actually work — pipelines, caches, instruction sets, and parallelism.",
        "content": """
        <p><strong>Computer architecture</strong> is the design of computer systems at
        the level between transistors and software. It answers: how do we organize
        billions of transistors into a machine that runs programs efficiently?</p>

        <h3>The Von Neumann Model</h3>
        <p>Almost every computer since 1945 follows the same basic blueprint:</p>
        <ul>
            <li><strong>CPU:</strong> Executes instructions.</li>
            <li><strong>Memory:</strong> Stores programs and data together.</li>
            <li><strong>I/O:</strong> Communicates with the outside world.</li>
            <li><strong>Bus:</strong> Connects everything.</li>
        </ul>

        <h3>Inside the CPU</h3>
        <ul>
            <li><strong>ALU:</strong> Arithmetic and logic operations.</li>
            <li><strong>Registers:</strong> Tiny, fast storage.</li>
            <li><strong>Control unit:</strong> Decodes and orchestrates.</li>
            <li><strong>Program counter:</strong> Points to the next instruction.</li>
            <li><strong>Instruction pipeline:</strong> Overlaps stages of execution.</li>
        </ul>

        <h3>Pipeline Stages</h3>
        <pre><code>Fetch → Decode → Execute → Memory → Write back

Multiple instructions in flight — 5× throughput
when perfectly pipelined.</code></pre>

        <h3>Memory Hierarchy</h3>
        <ul>
            <li><strong>Registers:</strong> ~1 cycle, bytes.</li>
            <li><strong>L1/L2/L3 caches:</strong> ~4–40 cycles, MB.</li>
            <li><strong>DRAM:</strong> ~200 cycles, GB.</li>
            <li><strong>SSD:</strong> ~100,000 cycles, TB.</li>
            <li><strong>HDD:</strong> ~10,000,000 cycles, TB.</li>
        </ul>

        <h3>Parallelism</h3>
        <ul>
            <li><strong>ILP:</strong> Instruction-level parallelism — superscalar
            execution.</li>
            <li><strong>SIMD:</strong> Single instruction, multiple data — vector
            processing.</li>
            <li><strong>Multicore:</strong> Multiple CPUs on one chip.</li>
            <li><strong>Multithreading:</strong> SMT / hyper-threading.</li>
            <li><strong>GPU:</strong> Thousands of simple cores for data-parallel
            work.</li>
        </ul>

        <h3>Instruction Set Architectures</h3>
        <ul>
            <li><strong>x86:</strong> Dominant on desktops and servers. Complex,
            backward-compatible.</li>
            <li><strong>ARM:</strong> Dominant on mobile and increasingly on laptops
            (Apple M-series).</li>
            <li><strong>RISC-V:</strong> Open-source, simple, growing rapidly.</li>
        </ul>
        """
    },

    "embedded-systems": {
        "title": "Embedded Systems",
        "icon": "🔌",
        "summary": "Computers hidden in everyday devices — microcontrollers, real-time, and IoT.",
        "content": """
        <p><strong>Embedded systems</strong> are computers built into other devices —
        cars, microwaves, pacemakers, satellites, door locks. They don't look like
        computers, but they're everywhere. You probably interact with dozens every
        day.</p>

        <h3>Characteristics</h3>
        <ul>
            <li><strong>Dedicated function:</strong> One job, done well.</li>
            <li><strong>Resource-constrained:</strong> Limited CPU, RAM, power.</li>
            <li><strong>Real-time:</strong> Must respond within deadlines.</li>
            <li><strong>Long-lived:</strong> Often must run for years without
            maintenance.</li>
            <li><strong>Reliable:</strong> Failures can be dangerous or fatal.</li>
        </ul>

        <h3>Microcontrollers vs Microprocessors</h3>
        <ul>
            <li><strong>MCU:</strong> CPU + RAM + flash + peripherals on one chip. Used
            in embedded.</li>
            <li><strong>MPU:</strong> Just the CPU. Needs external RAM and storage.</li>
            <li><strong>Popular MCUs:</strong> STM32, ESP32, AVR (Arduino), PIC, nRF.</li>
        </ul>

        <h3>Real-Time Systems</h3>
        <ul>
            <li><strong>Hard real-time:</strong> Missing a deadline is a failure.
            Airbags, pacemakers.</li>
            <li><strong>Firm real-time:</strong> Missing a deadline degrades quality.
            Multimedia.</li>
            <li><strong>Soft real-time:</strong> Missing a deadline is annoying but not
            fatal. Streaming.</li>
            <li><strong>RTOS:</strong> FreeRTOS, Zephyr, VxWorks. Scheduler with
            guarantees.</li>
        </ul>

        <h3>Example: Blinking an LED (Arduino)</h3>
        <pre><code>void setup() {
    pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(1000);
    digitalWrite(LED_BUILTIN, LOW);
    delay(1000);
}</code></pre>

        <h3>IoT (Internet of Things)</h3>
        <p>Embedded systems connected to the network. Billions of devices: smart
        thermostats, fitness trackers, industrial sensors, smart meters.</p>
        <ul>
            <li><strong>Protocols:</strong> MQTT, CoAP, BLE, Zigbee, LoRaWAN.</li>
            <li><strong>Security:</strong> Enormous challenge — devices often lack
            updates and encryption.</li>
            <li><strong>Edge computing:</strong> Processing data near the source.</li>
        </ul>
        """
    },

    "fpgas": {
        "title": "FPGAs & Reconfigurable Logic",
        "icon": "🧱",
        "summary": "Chips you can rewire — programmable logic between CPUs and ASICs.",
        "content": """
        <p>A <strong>Field-Programmable Gate Array (FPGA)</strong> is a chip whose
        internal logic can be reconfigured <em>after</em> manufacturing. Instead of
        running software, FPGAs implement circuits you design.</p>

        <h3>The Trade-off Triangle</h3>
        <ul>
            <li><strong>CPU:</strong> Flexible, easy to program, but slow.</li>
            <li><strong>ASIC:</strong> Fastest and most efficient, but frozen at
            manufacturing.</li>
            <li><strong>FPGA:</strong> Middle ground — fast like ASIC, reconfigurable
            like CPU.</li>
        </ul>

        <h3>How FPGAs Work</h3>
        <ul>
            <li><strong>Logic blocks (LUTs):</strong> Small lookup tables that implement
            arbitrary boolean functions.</li>
            <li><strong>Flip-flops:</strong> Store state.</li>
            <li><strong>Routing fabric:</strong> Wires that connect everything, configured
            at compile time.</li>
            <li><strong>I/O blocks:</strong> Connect to external signals.</li>
            <li><strong>DSP slices:</strong> Dedicated multipliers for signal
            processing.</li>
            <li><strong>Block RAM:</strong> On-chip memory.</li>
        </ul>

        <h3>Example: Verilog on an FPGA</h3>
        <pre><code>module counter(
    input wire clk,
    output reg [7:0] count
);
    always @(posedge clk) begin
        count &lt;= count + 1;
    end
endmodule</code></pre>

        <h3>When to Use an FPGA</h3>
        <ul>
            <li><strong>Low-volume products:</strong> Too costly to design an ASIC.</li>
            <li><strong>Evolving standards:</strong> Reconfigure when protocols
            change.</li>
            <li><strong>High-speed signal processing:</strong> Radar, software-defined
            radio.</li>
            <li><strong>Prototyping:</strong> Before committing to an ASIC.</li>
            <li><strong>Data center acceleration:</strong> Microsoft Bing, AWS F1.</li>
        </ul>

        <h3>Big Players</h3>
        <ul>
            <li><strong>AMD (Xilinx):</strong> Largest FPGA vendor.</li>
            <li><strong>Intel (Altera):</strong> Second-largest.</li>
            <li><strong>Lattice, Microchip:</strong> Smaller, specialized.</li>
        </ul>
        """
    },

    "robotics": {
        "title": "Robotics",
        "icon": "🦾",
        "summary": "Machines that sense, think, and act in the physical world.",
        "content": """
        <p><strong>Robotics</strong> is the engineering of machines that sense their
        environment, make decisions, and act physically. It combines mechanical
        engineering, electrical engineering, and computer science.</p>

        <h3>The Sense-Think-Act Loop</h3>
        <ul>
            <li><strong>Sense:</strong> Sensors capture the world (cameras, LIDAR,
            IMUs, encoders, force sensors).</li>
            <li><strong>Think:</strong> Algorithms plan paths, recognize objects, and
            decide actions.</li>
            <li><strong>Act:</strong> Motors, servos, and actuators move the robot.</li>
        </ul>

        <h3>Robot Components</h3>
        <ul>
            <li><strong>Chassis:</strong> Physical body.</li>
            <li><strong>Actuators:</strong> DC motors, steppers, servos, pneumatics.</li>
            <li><strong>Sensors:</strong> Range, vision, force, current.</li>
            <li><strong>Controller:</strong> MCU or SBC (Raspberry Pi, Jetson).</li>
            <li><strong>Power:</strong> Battery, regulator, motor driver.</li>
            <li><strong>Communication:</strong> I2C, SPI, UART, CAN.</li>
        </ul>

        <h3>Types of Robots</h3>
        <ul>
            <li><strong>Industrial:</strong> Fixed arms on production lines.</li>
            <li><strong>Mobile:</strong> Wheels, tracks, or legs.</li>
            <li><strong>Aerial:</strong> Drones, quadcopters.</li>
            <li><strong>Underwater:</strong> ROVs, AUVs.</li>
            <li><strong>Humanoid:</strong> Bipedal (Boston Dynamics, Tesla Optimus).</li>
            <li><strong>Swarm:</strong> Many simple robots cooperating.</li>
        </ul>

        <h3>Key Algorithms</h3>
        <ul>
            <li><strong>SLAM:</strong> Simultaneous localization and mapping.</li>
            <li><strong>Path planning:</strong> A*, RRT, potential fields.</li>
            <li><strong>Control:</strong> PID, MPC, impedance control.</li>
            <li><strong>Computer vision:</strong> Object detection, pose estimation.</li>
            <li><strong>Reinforcement learning:</strong> Learned locomotion, grasping.</li>
        </ul>

        <h3>Framework: ROS</h3>
        <p>The Robot Operating System (ROS) is the de-facto standard middleware.
        Nodes communicate via topics, services, and actions. Packages exist for
        almost every robot, sensor, and algorithm.</p>
        """
    },

    "hardware-security": {
        "title": "Hardware Security",
        "icon": "🔐",
        "summary": "Protecting chips from physical attacks, side channels, and tampering.",
        "content": """
        <p><strong>Hardware security</strong> deals with attacks that exploit physical
        properties of chips — power consumption, electromagnetic emissions, timing —
        and with designing chips that resist tampering.</p>

        <h3>Why Hardware Security Matters</h3>
        <p>Software can be patched; hardware cannot. Once a chip ships with a flaw,
        every device containing it is vulnerable forever. This makes hardware attacks
        especially dangerous.</p>

        <h3>Threat Categories</h3>
        <ul>
            <li><strong>Side-channel attacks:</strong> Extract secrets from power,
            timing, or EM emissions.</li>
            <li><strong>Fault injection:</strong> Glitch voltage, clock, or temperature
            to cause errors.</li>
            <li><strong>Physical probing:</strong> Microprobing, focused ion beams.</li>
            <li><strong>Reverse engineering:</strong> Decapping and imaging to reveal
            design.</li>
            <li><strong>Supply chain:</strong> Tampered chips or IP inserted at
            fabrication.</li>
        </ul>

        <h3>Side-Channel Example: Timing Attack</h3>
        <pre><code>def insecure_compare(a, b):
    for x, y in zip(a, b):
        if x != y:
            return False       # leaks: exits early
    return True

# Attacker measures how long the function takes
# → learns how many bytes matched → guesses password byte by byte

def secure_compare(a, b):
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y        # constant time
    return result == 0</code></pre>

        <h3>Defenses</h3>
        <ul>
            <li><strong>Constant-time code:</strong> No data-dependent branches or
            memory access.</li>
            <li><strong>Masking:</strong> Randomize intermediate values.</li>
            <li><strong>Secure enclaves:</strong> ARM TrustZone, Intel SGX.</li>
            <li><strong>Physical shielding:</strong> Tamper-resistant packaging.</li>
            <li><strong>PUFs (Physically Unclonable Functions):</strong> Derive keys
            from manufacturing variation.</li>
            <li><strong>Secure boot:</strong> Cryptographically verify firmware at
            startup.</li>
        </ul>

        <h3>Applications</h3>
        <ul>
            <li><strong>Smart cards:</strong> Credit cards, SIM cards, passports.</li>
            <li><strong>TPM chips:</strong> Trusted Platform Module on PCs.</li>
            <li><strong>HSMs:</strong> Hardware Security Modules for servers.</li>
            <li><strong>Cryptocurrency wallets:</strong> Hardware wallets like
            Ledger.</li>
            <li><strong>Military:</strong> Anti-tamper designs.</li>
        </ul>
        """
    },

    # ════════════════════════════════════════════════════════════
    # PHYSICS
    # ════════════════════════════════════════════════════════════
    "quantum-mechanics": {
        "title": "Quantum Mechanics",
        "icon": "⚛️",
        "summary": "The strange physics of the very small — waves, uncertainty, and entanglement.",
        "content": """
        <p><strong>Quantum mechanics</strong> describes physics at the scale of atoms and
        subatomic particles. Its predictions are wildly counterintuitive, yet it's the
        most precisely tested theory in all of science.</p>

        <h3>The Big Ideas</h3>
        <ul>
            <li><strong>Wave-particle duality:</strong> Light and matter behave as both
            waves and particles.</li>
            <li><strong>Quantization:</strong> Energy comes in discrete packets
            (quanta).</li>
            <li><strong>Superposition:</strong> A particle can be in multiple states at
            once — until measured.</li>
            <li><strong>Wavefunction:</strong> The mathematical description of a quantum
            system.</li>
            <li><strong>Uncertainty principle:</strong> You cannot know both position
            and momentum precisely.</li>
            <li><strong>Entanglement:</strong> Two particles can be correlated in ways
            no classical theory can explain.</li>
            <li><strong>Collapse:</strong> Measurement forces one outcome from many.</li>
        </ul>

        <h3>Schrödinger Equation</h3>
        <pre><code>iℏ ∂ψ/∂t = Ĥ ψ

ψ = wavefunction
Ĥ = Hamiltonian operator
ℏ = reduced Planck constant</code></pre>

        <h3>Quantum Computing</h3>
        <p>Computers that manipulate quantum states as qubits (0, 1, or both at once).
        Potentially exponential speedups for specific problems:</p>
        <ul>
            <li><strong>Shor's algorithm:</strong> Factors integers — threatens RSA.</li>
            <li><strong>Grover's algorithm:</strong> Quadratic speedup for search.</li>
            <li><strong>Quantum simulation:</strong> Chemistry, materials.</li>
        </ul>

        <h3>Applications of Quantum Mechanics</h3>
        <ul>
            <li><strong>Semiconductors:</strong> The band structure that makes chips
            work.</li>
            <li><strong>Lasers:</strong> Stimulated emission of photons.</li>
            <li><strong>MRI:</strong> Nuclear magnetic resonance imaging.</li>
            <li><strong>Atomic clocks:</strong> GPS relies on them.</li>
            <li><strong>Quantum cryptography:</strong> Provably secure key exchange.</li>
        </ul>
        """
    },

    "electromagnetism": {
        "title": "Electromagnetism",
        "icon": "🧲",
        "summary": "Electric and magnetic fields — the force that binds atoms and drives every circuit.",
        "content": """
        <p><strong>Electromagnetism</strong> is the study of electric and magnetic
        fields and their interactions with matter. It's one of the four fundamental
        forces, and the one that governs virtually all of our everyday experience.</p>

        <h3>Maxwell's Equations</h3>
        <p>Four equations that summarize the entirety of classical electromagnetism:</p>
        <ol>
            <li><strong>Gauss's law:</strong> Electric fields diverge from charges.</li>
            <li><strong>Gauss's law for magnetism:</strong> No magnetic monopoles.</li>
            <li><strong>Faraday's law:</strong> Changing magnetic field induces
            electric field.</li>
            <li><strong>Ampère-Maxwell law:</strong> Current and changing electric field
            create magnetic field.</li>
        </ol>
        <p>From these four equations — plus the Lorentz force — everything else follows:
        light, circuits, antennas, motors, generators, transformers.</p>

        <h3>Core Concepts</h3>
        <ul>
            <li><strong>Electric charge:</strong> Positive and negative. Conservation
            law.</li>
            <li><strong>Electric field (E):</strong> Force per unit charge.</li>
            <li><strong>Magnetic field (B):</strong> Created by moving charges.</li>
            <li><strong>Electromagnetic waves:</strong> Light, radio, X-rays — all the
            same phenomenon at different frequencies.</li>
            <li><strong>Induction:</strong> Changing fields create current. Basis of
            every generator.</li>
        </ul>

        <h3>The Electromagnetic Spectrum</h3>
        <ul>
            <li><strong>Radio:</strong> AM, FM, Wi-Fi, cellular.</li>
            <li><strong>Microwave:</strong> Radar, microwave ovens, 5G.</li>
            <li><strong>Infrared:</strong> Heat, remote controls.</li>
            <li><strong>Visible:</strong> Red to violet — the narrow band we see.</li>
            <li><strong>Ultraviolet:</strong> Sunburns, sterilization.</li>
            <li><strong>X-ray:</strong> Medical imaging, crystallography.</li>
            <li><strong>Gamma:</strong> Nuclear decay, cancer treatment.</li>
        </ul>

        <h3>Applications</h3>
        <ul>
            <li><strong>Motors and generators:</strong> Mechanical ↔ electrical energy.</li>
            <li><strong>Transformers:</strong> Step voltages up/down.</li>
            <li><strong>Wireless:</strong> Antennas radiate and receive EM waves.</li>
            <li><strong>Magnetic storage:</strong> HDDs, tape.</li>
            <li><strong>Medical:</strong> MRI, X-ray, TMS.</li>
        </ul>
        """
    },

    "thermodynamics": {
        "title": "Thermodynamics",
        "icon": "🔥",
        "summary": "Heat, work, and entropy — the physics of energy and its limits.",
        "content": """
        <p><strong>Thermodynamics</strong> deals with heat, work, temperature, and
        energy. It governs everything from steam engines to black holes — and it sets
        fundamental limits on what computers can do.</p>

        <h3>The Four Laws</h3>
        <ul>
            <li><strong>Zeroth law:</strong> If A is in equilibrium with B, and B with
            C, then A is with C. (Defines temperature.)</li>
            <li><strong>First law:</strong> Energy is conserved. ΔU = Q − W.</li>
            <li><strong>Second law:</strong> Entropy of an isolated system never
            decreases. Heat flows from hot to cold.</li>
            <li><strong>Third law:</strong> Entropy approaches a minimum as temperature
            approaches absolute zero.</li>
        </ul>

        <h3>Key Concepts</h3>
        <ul>
            <li><strong>Temperature:</strong> Average kinetic energy of particles.</li>
            <li><strong>Heat:</strong> Energy transfer due to temperature difference.</li>
            <li><strong>Work:</strong> Energy transfer due to force × distance.</li>
            <li><strong>Internal energy:</strong> Total energy stored in a system.</li>
            <li><strong>Entropy:</strong> Measure of disorder or information.</li>
            <li><strong>Enthalpy:</strong> U + PV, useful for chemistry.</li>
        </ul>

        <h3>Why CS Cares</h3>
        <p>Thermodynamics sets hard limits on computing:</p>
        <ul>
            <li><strong>Landauer's principle:</strong> Erasing one bit dissipates at
            least kT·ln(2) energy.</li>
            <li><strong>Heat dissipation:</strong> Every operation generates heat — a
            major bottleneck in CPUs.</li>
            <li><strong>Reversible computing:</strong> If we could compute without
            erasing bits, we could approach zero energy.</li>
            <li><strong>Data centers:</strong> Cool billions of dollars each year.</li>
        </ul>

        <h3>Applications</h3>
        <ul>
            <li><strong>Engines:</strong> Carnot, Otto, Diesel cycles.</li>
            <li><strong>Refrigeration:</strong> Heat pumps, air conditioning.</li>
            <li><strong>Materials:</strong> Phase transitions, crystal growth.</li>
            <li><strong>Astrophysics:</strong> Stellar evolution, black holes.</li>
            <li><strong>Information theory:</strong> Entropy as information.</li>
        </ul>
        """
    },

    "optics": {
        "title": "Optics",
        "icon": "🔭",
        "summary": "Light, lenses, lasers, and photonics — how we control electromagnetic waves.",
        "content": """
        <p><strong>Optics</strong> is the study of light — how it's generated, propagates,
        interacts with matter, and is detected. It's essential for cameras, displays,
        fiber optics, lasers, and quantum computing.</p>

        <h3>Wave Optics vs Ray Optics</h3>
        <ul>
            <li><strong>Ray optics (geometric):</strong> Light travels in straight lines.
            Good for lenses and mirrors.</li>
            <li><strong>Wave optics (physical):</strong> Light is a wave. Necessary for
            interference and diffraction.</li>
        </ul>

        <h3>Core Concepts</h3>
        <ul>
            <li><strong>Reflection:</strong> Light bounces off surfaces.</li>
            <li><strong>Refraction:</strong> Light bends when entering a new medium.
            Snell's law.</li>
            <li><strong>Diffraction:</strong> Waves spread when passing through gaps.</li>
            <li><strong>Interference:</strong> Waves add or cancel. Basis of
            holography.</li>
            <li><strong>Polarization:</strong> Light's electric field orientation.</li>
            <li><strong>Dispersion:</strong> Different colors refract differently — why
            prisms split light.</li>
        </ul>

        <h3>Lasers</h3>
        <p>Light Amplification by Stimulated Emission of Radiation. Key properties:</p>
        <ul>
            <li><strong>Coherent:</strong> All waves in phase.</li>
            <li><strong>Monochromatic:</strong> Single wavelength.</li>
            <li><strong>Collimated:</strong> Narrow, parallel beam.</li>
            <li><strong>Intense:</strong> High power density.</li>
        </ul>
        <p>Used in: barcode scanners, surgery, fiber communications, CD/DVD, industrial
        cutting, weapons.</p>

        <h3>Fiber Optics</h3>
        <p>Light guided through glass fibers by total internal reflection. The backbone
        of the internet:</p>
        <ul>
            <li><strong>Single-mode:</strong> ~9 µm core, long-distance.</li>
            <li><strong>Multi-mode:</strong> ~50 µm core, short-distance.</li>
            <li><strong>WDM:</strong> Many wavelengths in one fiber.</li>
            <li><strong>Speed:</strong> Terabits per second over transoceanic
            cables.</li>
        </ul>

        <h3>Applications</h3>
        <ul>
            <li><strong>Cameras:</strong> Lenses, sensors, image processing.</li>
            <li><strong>Displays:</strong> LCD, OLED, microLED.</li>
            <li><strong>Medical:</strong> Endoscopy, laser surgery, OCT.</li>
            <li><strong>Manufacturing:</strong> Laser cutting, welding, 3D printing.</li>
            <li><strong>Quantum:</strong> Photonic qubits, quantum key distribution.</li>
        </ul>
        """
    },

    "relativity": {
        "title": "Relativity",
        "icon": "🌌",
        "summary": "Einstein's theories of space, time, gravity, and the cosmos.",
        "content": """
        <p><strong>Relativity</strong> is Einstein's reformulation of space, time, and
        gravity. It replaced Newtonian mechanics for high speeds and strong
        gravitational fields, and it's essential for GPS, particle physics, and
        cosmology.</p>

        <h3>Special Relativity (1905)</h3>
        <p>Two postulates:</p>
        <ol>
            <li>The laws of physics are the same in all inertial frames.</li>
            <li>The speed of light in vacuum is constant, regardless of observer.</li>
        </ol>
        <p>Consequences:</p>
        <ul>
            <li><strong>Time dilation:</strong> Moving clocks run slow.</li>
            <li><strong>Length contraction:</strong> Moving objects shorten in
            direction of motion.</li>
            <li><strong>Relativity of simultaneity:</strong> Events simultaneous in one
            frame may not be in another.</li>
            <li><strong>Mass-energy equivalence:</strong> E = mc².</li>
            <li><strong>Speed limit:</strong> Nothing travels faster than light.</li>
        </ul>

        <h3>General Relativity (1915)</h3>
        <p>Gravity is not a force — it's the curvature of spacetime caused by mass and
        energy. Objects follow the straightest possible paths in curved spacetime.</p>
        <ul>
            <li><strong>Gravitational time dilation:</strong> Clocks run slower near
            massive objects.</li>
            <li><strong>Gravitational lensing:</strong> Light bends around massive
            objects.</li>
            <li><strong>Black holes:</strong> Regions where spacetime curvature becomes
            infinite.</li>
            <li><strong>Gravitational waves:</strong> Ripples in spacetime, detected in
            2015.</li>
            <li><strong>Expanding universe:</strong> Big Bang cosmology.</li>
        </ul>

        <h3>Why CS Cares</h3>
        <ul>
            <li><strong>GPS satellites:</strong> Must correct for both special and
            general relativistic effects — otherwise position errors grow by ~10 km
            per day.</li>
            <li><strong>Particle accelerators:</strong> Relativistic mechanics needed to
            design magnets and targets.</li>
            <li><strong>Atomic clocks:</strong> Rely on relativity for precision.</li>
            <li><strong>Quantum field theory:</strong> Requires special relativity for
            consistency.</li>
        </ul>

        <h3>Example: Time Dilation</h3>
        <pre><code>Δt' = Δt / √(1 - v²/c²)

At v = 0.87c:
√(1 - 0.87²) ≈ 0.5
Δt' = 2 × Δt

A year on the ship = two years on Earth.</code></pre>

        <h3>Applications</h3>
        <ul>
            <li><strong>GPS and GNSS:</strong> Relativistic corrections.</li>
            <li><strong>Nuclear power:</strong> E = mc².</li>
            <li><strong>Particle physics:</strong> Colliders, cosmic rays.</li>
            <li><strong>Astrophysics:</strong> Black holes, neutron stars, cosmology.</li>
            <li><strong>Gravitational wave astronomy:</strong> LIGO, Virgo.</li>
        </ul>
        """
    }
}


BRANCHES = {
    "cs": {
        "title": "Computer Science",
        "icon": "💻",
        "color": "sage",
        "tagline": "The study of computation, information, and automation.",
        "intro": """
        <p><strong>Computer Science</strong> is not really about computers — it's about
        <em>computation</em>. It asks: what problems can be solved by a step-by-step
        procedure, how efficiently can we solve them, and what are the fundamental
        limits?</p>
        <p>CS spans an enormous range — from the abstract mathematics of complexity
        theory to the deeply practical engineering of web servers. It has produced some
        of the most transformative technologies in human history.</p>
        """,
        "topics": [
            "algorithms",
            "data-structures",
            "ai-ml",
            "operating-systems",
            "networking",
            "databases",
        ],
    },
    "semiconductors": {
        "title": "Semiconductors",
        "icon": "🔬",
        "color": "amber",
        "tagline": "The physics and engineering behind transistors, chips, and modern electronics.",
        "intro": """
        <p><strong>Semiconductors</strong> are materials whose conductivity lies between
        that of a conductor and an insulator — and whose conductivity can be precisely
        <em>controlled</em>.</p>
        <p>The field sits at the intersection of quantum physics, materials science,
        chemistry, and industrial engineering. From the discovery of the transistor in
        1947 to the 2-nanometer chips of today, semiconductors have reshaped the
        world.</p>
        """,
        "topics": [
            "semiconductor-physics",
            "transistors",
            "chip-fabrication",
            "integrated-circuits",
            "beyond-silicon",
        ],
    },
    "ee": {
        "title": "Electrical Engineering",
        "icon": "⚡",
        "color": "olive",
        "tagline": "The study of electricity, circuits, signals, and power systems.",
        "intro": """
        <p><strong>Electrical Engineering (EE)</strong> is the discipline that deals
        with electricity in all its forms — from microscopic currents inside a
        transistor to continent-spanning power grids.</p>
        <p>EE is a vast field, encompassing analog and digital circuits, signal
        processing, control systems, electromagnetics, power engineering, and
        communications.</p>
        """,
        "topics": [
            "circuit-analysis",
            "digital-logic",
            "signals-systems",
            "power-systems",
            "control-systems",
        ],
    },
    "math": {
        "title": "Mathematics",
        "icon": "🧮",
        "color": "cyan",
        "tagline": "The universal language — vectors, calculus, logic, and probability.",
        "intro": """
        <p><strong>Mathematics</strong> is the language in which the universe is
        written. It's also the language of computer science — algorithms, machine
        learning, cryptography, and graphics all rest on mathematical foundations.</p>
        <p>This branch covers the mathematics most relevant to computing: linear
        algebra (vectors and matrices), calculus (rates of change), discrete math
        (logic and graphs), probability (reasoning under uncertainty), and number
        theory (primes and modular arithmetic).</p>
        """,
        "topics": [
            "linear-algebra",
            "calculus",
            "discrete-math",
            "probability",
            "number-theory",
        ],
    },
    "computer-engineering": {
        "title": "Computer Engineering",
        "icon": "🛠️",
        "color": "violet",
        "tagline": "Hardware and software meet — architecture, embedded systems, and robotics.",
        "intro": """
        <p><strong>Computer Engineering</strong> sits at the boundary between electrical
        engineering and computer science. It deals with how hardware and software
        interact — from the CPU design down to the circuits, and up to the systems that
        run them.</p>
        <p>Where CS asks "what can be computed?", computer engineering asks "how do we
        build machines that compute?" It covers processor design, embedded systems,
        FPGAs, robotics, and hardware security.</p>
        """,
        "topics": [
            "computer-architecture",
            "embedded-systems",
            "fpgas",
            "robotics",
            "hardware-security",
        ],
    },
    "physics": {
        "title": "Physics",
        "icon": "🌌",
        "color": "pink",
        "tagline": "The fundamental laws governing matter, energy, space, and time.",
        "intro": """
        <p><strong>Physics</strong> is the study of the fundamental laws of nature —
        matter, energy, forces, space, and time. It's the most basic of the sciences,
        and the source of all the principles that engineering applies.</p>
        <p>Semiconductors are quantum mechanics. Lasers are optics. GPS is relativity.
        Every technology that seems "pure CS" traces back to physics at the bottom.</p>
        """,
        "topics": [
            "quantum-mechanics",
            "electromagnetism",
            "thermodynamics",
            "optics",
            "relativity",
        ],
    },
}


# ════════════════════════════════════════════════════════════
# USER HELPERS
# ════════════════════════════════════════════════════════════

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt + "$" + hashed


def verify_password(password, stored):
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hash_password(password, salt) == stored


def load_users():
    users = {}
    if not os.path.exists(USERS_FILE):
        return users
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 3:
                continue
            users[parts[0]] = {
                "password": parts[1],
                "created": parts[2],
                "display_name": parts[3] if len(parts) > 3 else parts[0],
                "bio": parts[4] if len(parts) > 4 else "",
                "favorite": parts[5] if len(parts) > 5 else "",
            }
    return users


def save_user(username, password):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hashed = hash_password(password)
    with open(USERS_FILE, "a", encoding="utf-8") as f:
        f.write(username + "|" + hashed + "|" + timestamp + "|" + username + "||\n")


def rewrite_all_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        for username, info in users.items():
            display = info.get("display_name", username) or username
            bio = info.get("bio", "").replace("|", "/").replace("\n", " ")
            fav = info.get("favorite", "").replace("|", "/").replace("\n", " ")
            f.write("|".join([
                username,
                info["password"],
                info["created"],
                display,
                bio,
                fav,
            ]) + "\n")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def get_related_topics(current_slug, limit=3):
    current_branch = None
    for bslug, branch in BRANCHES.items():
        if current_slug in branch["topics"]:
            current_branch = bslug
            break

    related = []
    if current_branch:
        for tslug in BRANCHES[current_branch]["topics"]:
            if tslug != current_slug:
                related.append(tslug)

    for bslug, branch in BRANCHES.items():
        if bslug == current_branch:
            continue
        for tslug in branch["topics"]:
            if tslug != current_slug and tslug not in related:
                related.append(tslug)
            if len(related) >= limit:
                break
        if len(related) >= limit:
            break

    return {slug: TOPICS[slug] for slug in related[:limit] if slug in TOPICS}


def get_branch_for_topic(slug):
    for bslug, branch in BRANCHES.items():
        if slug in branch["topics"]:
            return bslug, branch
    return None, None


# ════════════════════════════════════════════════════════════
# CONTEXT PROCESSOR
# ════════════════════════════════════════════════════════════

@app.context_processor
def inject_globals():
    return {
        "topics": TOPICS,
        "branches": BRANCHES,
    }


# ════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════

@app.route("/")
def welcome_page():
    return render_template("welcome.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("register"))

        if len(username) > 30:
            flash("Username must be 30 characters or fewer.", "error")
            return redirect(url_for("register"))

        if len(password) < 4:
            flash("Password must be at least 4 characters.", "error")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        users = load_users()
        if username in users:
            flash("That username is already taken.", "error")
            return redirect(url_for("register"))

        save_user(username, password)
        session["username"] = username
        flash("Welcome, " + username + "!", "success")
        return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        users = load_users()
        user = users.get(username)

        if not user or not verify_password(password, user["password"]):
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

        session["username"] = username
        flash("Welcome back, " + username + "!", "success")
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You've been logged out.", "success")
    return redirect(url_for("welcome_page"))


@app.route("/home")
@login_required
def home():
    return render_template("home.html", branches=BRANCHES, visitor_name=session["username"])


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    username = session["username"]
    users = load_users()
    user_info = users.get(username, {})

    if request.method == "POST":
        action = request.form.get("action", "update")

        if action == "update":
            display_name = request.form.get("display_name", "").strip()[:40]
            bio = request.form.get("bio", "").strip()[:280]
            favorite = request.form.get("favorite", "").strip()[:60]

            user_info["display_name"] = display_name or username
            user_info["bio"] = bio
            user_info["favorite"] = favorite

            users[username] = user_info
            rewrite_all_users(users)

            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile"))

        elif action == "delete":
            confirm = request.form.get("confirm_delete", "").strip()
            if confirm == username:
                del users[username]
                rewrite_all_users(users)
                session.pop("username", None)
                flash("Your account has been deleted.", "success")
                return redirect(url_for("welcome_page"))
            else:
                flash("Type your username exactly to confirm deletion.", "error")
                return redirect(url_for("profile"))

    joined_dt = None
    try:
        joined_dt = datetime.strptime(user_info.get("created", ""), "%Y-%m-%d %H:%M:%S")
        days = (datetime.now() - joined_dt).days
        if days == 0:
            age = "today"
        elif days == 1:
            age = "1 day"
        else:
            age = f"{days} days"
    except Exception:
        age = "unknown"

    return render_template(
        "profile.html",
        username=username,
        user_info=user_info,
        account_age=age,
    )


@app.route("/topics")
def topics():
    return render_template("topics.html", topics=TOPICS)


@app.route("/branch/<slug>")
def branch_detail(slug):
    branch = BRANCHES.get(slug)
    if not branch:
        abort(404)
    branch_topics = {k: TOPICS[k] for k in branch["topics"] if k in TOPICS}
    return render_template("branch.html", branch=branch, branch_topics=branch_topics, slug=slug)


@app.route("/topic/<slug>")
def topic_detail(slug):
    topic = TOPICS.get(slug)
    if not topic:
        abort(404)
    branch_slug, branch = get_branch_for_topic(slug)
    related = get_related_topics(slug, limit=3)
    return render_template(
        "topic.html",
        topic=topic,
        slug=slug,
        topics=TOPICS,
        branch_slug=branch_slug,
        branch=branch,
        related=related,
    )


@app.route("/visitors")
def visitors():
    users = load_users()
    entries = [
        {"username": name, "created": info["created"]}
        for name, info in users.items()
    ]
    entries.reverse()
    return render_template("visitors.html", entries=entries, total=len(entries))

# ────────────────────────────────────────────────────────────
# INTERACTIVE ROUTES
# ────────────────────────────────────────────────────────────

@app.route("/quiz/<slug>", methods=["GET", "POST"])
def quiz(slug):
    questions = QUIZZES.get(slug)
    topic = TOPICS.get(slug)
    if not questions or not topic:
        abort(404)

    if request.method == "POST":
        score = 0
        results = []
        for i, q in enumerate(questions):
            user_answer = request.form.get(f"q{i}")
            correct = user_answer is not None and int(user_answer) == q["answer"]
            if correct:
                score += 1
            results.append({
                "question": q["q"],
                "options": q["options"],
                "user": int(user_answer) if user_answer is not None else -1,
                "correct_index": q["answer"],
                "correct": correct,
            })
        return render_template("quiz_results.html", slug=slug, topic=topic, score=score, total=len(questions), results=results)

    return render_template("quiz.html", slug=slug, topic=topic, questions=questions)


@app.route("/guestbook", methods=["GET", "POST"])
def guestbook():
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:40]
        message = request.form.get("message", "").strip()[:280]
        if name and message:
            save_guestbook_entry(name, message)
            flash("Thanks for signing the guestbook!", "success")
        return redirect(url_for("guestbook"))

    entries = load_guestbook()
    entries.reverse()
    return render_template("guestbook.html", entries=entries, total=len(entries))


@app.route("/random-fact")
def random_fact():
    import random
    slug = random.choice(list(TOPICS.keys()))
    topic = TOPICS[slug]
    return redirect(url_for("topic_detail", slug=slug))


@app.route("/progress")
def progress():
    if "username" not in session:
        flash("Log in to track your progress.", "warning")
        return redirect(url_for("login"))
    return render_template("progress.html", topics=TOPICS, branches=BRANCHES)


@app.route("/api/mark-read/<slug>", methods=["POST"])
def mark_read(slug):
    if "username" not in session:
        return {"ok": False, "error": "not logged in"}, 401
    if slug not in TOPICS:
        return {"ok": False, "error": "unknown topic"}, 404

    username = session["username"]
    entries = []
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            entries = [l.strip() for l in f if l.strip()]

    key = username + "::" + slug
    if key not in entries:
        entries.append(key)
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(entries))

    return {"ok": True, "slug": slug}

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.context_processor
def inject_globals():
    return {
        "topics": TOPICS,
        "branches": BRANCHES,
        "QUIZZES": QUIZZES,   # ← ADD THIS
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)