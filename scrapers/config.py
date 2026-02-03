"""
Configuration for scrapers.
"""

# ERIC API Configuration
ERIC_API_BASE = "https://api.ies.ed.gov/eric/"
ERIC_SEARCH_ENDPOINT = "https://api.ies.ed.gov/eric/"

# Special education search terms for ERIC API
# These are keyword searches, not ERIC descriptors
ERIC_DESCRIPTORS = [
    "autism teaching strategies classroom",
    "ADHD classroom intervention strategies",
    "learning disabilities teaching methods",
    "dyslexia reading intervention",
    "special education behavior management",
    "IEP goals accommodations",
    "inclusive education strategies",
    "differentiated instruction special needs",
    "applied behavior analysis classroom",
    "social skills training autism",
    "self regulation strategies students",
    "executive function intervention",
    "sensory processing classroom strategies",
    "emotional behavioral disorders intervention",
]

# Additional specific keyword searches
ERIC_KEYWORDS = [
    "evidence-based practices special education",
    "visual supports autism spectrum",
    "behavior intervention plan school",
    "assistive technology learning disabilities",
    "social emotional learning disabilities",
    "transition planning special education",
    "positive behavior support PBIS",
    "universal design learning UDL",
    "response to intervention RTI",
    "functional behavior assessment",
]

# IRIS Center Configuration
IRIS_BASE_URL = "https://iris.peabody.vanderbilt.edu"

# IRIS module categories and URLs
IRIS_MODULES = {
    "autism": [
        "/module/asd1/",  # Autism Spectrum Disorder (Part 1)
        "/module/asd2/",  # Autism Spectrum Disorder (Part 2)
    ],
    "behavior": [
        "/module/bi1/",   # Behavior Intervention (Part 1)
        "/module/bi2/",   # Behavior Intervention (Part 2)
        "/module/beh1/",  # Addressing Challenging Behaviors (Part 1)
        "/module/beh2/",  # Addressing Challenging Behaviors (Part 2)
        "/module/fba/",   # Functional Behavioral Assessment
        "/module/pbis/",  # PBIS: An Overview for Educators
    ],
    "learning_disabilities": [
        "/module/rti01/",  # RTI (Part 1)
        "/module/rti02/",  # RTI (Part 2)
        "/module/dbi1/",   # Data-Based Individualization
        "/module/rs/",     # Reading Strategies
    ],
    "classroom_management": [
        "/module/sr/",     # Self-Regulation
        "/module/ecbm/",   # Early Childhood Behavior Management
        "/module/beh-elem/", # Behavior Elementary
    ],
    "instruction": [
        "/module/di/",     # Differentiated Instruction
        "/module/udl/",    # Universal Design for Learning
        "/module/sca/",    # Student-Centered Learning
        "/module/csr/",    # Content Enhancement Routines
    ],
    "assessment": [
        "/module/pm/",     # Progress Monitoring
        "/module/basc/",   # Behavior Assessment
    ],
    "collaboration": [
        "/module/coteach/", # Co-Teaching
        "/module/fam/",     # Family Engagement
    ],
    "transition": [
        "/module/tran-sit/", # Transition Planning
    ],
}

# IRIS resource pages (non-module content)
IRIS_RESOURCE_PAGES = [
    "/resources/ebp_summaries/",  # Evidence-Based Practice Summaries
    "/resources/case-studies/",   # Case Studies
]

# Disability type mappings
DISABILITY_MAPPINGS = {
    "autism": ["autism", "asd", "autism spectrum", "asperger"],
    "adhd": ["adhd", "attention deficit", "hyperactivity", "add"],
    "learning_disabilities": ["learning disabilit", "dyslexia", "dyscalculia", "dysgraphia", "ld"],
    "emotional_behavioral": ["emotional", "behavioral", "behavior disorder", "ebd", "conduct"],
    "sensory_processing": ["sensory", "sensory processing", "sensory integration"],
    "intellectual": ["intellectual disabilit", "cognitive disabilit", "developmental delay"],
}

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between requests
MAX_RETRIES = 3

# Output settings
OUTPUT_DIR = "data/scraped"
