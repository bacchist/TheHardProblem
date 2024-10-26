from autogen import AssistantAgent, Cache, GroupChat, GroupChatManager
import json
import os
import logging
import re

# Ensure necessary directories exist
os.makedirs("output", exist_ok=True)

# Configuration for LLM
config_list = [
    {
        'model': 'gpt-4o-mini',
        'api_key': os.getenv('OPENAI_API_KEY')
    }
]

llm_config = {
    "config_list": config_list,
    "temperature": 0.0
}

# Function to extract JSON from agent output
def extract_json_from_output(output):
    match = re.search(r'```json\s*(\{.*?\})\s*```', output, re.DOTALL)
    if match:
        return match.group(1)
    else:
        return None

# Define agents with their system messages
theory_summarizer = AssistantAgent(
    name="TheorySummarizer",
    system_message=(
        "You are responsible for identifying and summarizing theories of consciousness from text sections.\n\n"
        "**Responsibilities:**\n"
        "- Identify theories mentioned in the text.\n"
        "- Summarize each theory.\n"
        "- **Guideline 1:** If an author is mentioned by name in the section title, consider them the primary theorist (Author) for that section.\n"
        "- **Guideline 2:** Identify broader Categories which may have many associated Theories.\n"
        "- **Guideline 3:** There will rarely be more than one theory per section. If there is more than one theory, consider the most relevant theory.\n\n"
        "**Output Format:**\n"
        "Provide your findings in JSON format with the following structure:\n"
        "```json\n"
        "{\n"
        "  \"theory\": {\n"
        "    \"name\": \"...\",\n"
        "    \"description\": \"...\",\n"
        "    \"categories\": [\"...\"]\n"
        "  }\n"
        "}\n"
        "```\n"
        "**Example Output:**\n"
        "```json\n"
        "{\n"
        "  \"theory\": {\n"
        "    \"name\": \"Integrated Information Theory\",\n"
        "    \"description\": \"A theory that proposes consciousness corresponds to the capacity of a system to integrate information.\",\n"
        "    \"categories\": [\"Information Processing\", \"Neuroscience\"]\n"
        "  }\n"
        "}\n"
        "```\n"
        "Ensure that your output is valid JSON for further processing."
        "**Important:** Output only the JSON code block as specified above, without any additional text or explanations."
    ),
    llm_config=llm_config,
)

author_curator = AssistantAgent(
    name="AuthorCurator",
    system_message=(
        "You are responsible for identifying theorists, validating their relevance, and creating short biographies.\n\n"
        "**Responsibilities:**\n"
        "- Identify authors mentioned in the text.\n"
        "- Determine if they are the primary theorist for the section (if mentioned in the section title).\n"
        "- **Guideline 1:** If an author is mentioned by name in the section title, consider them the primary theorist (Author) for that section.\n"
        "- **Guideline 2:** There will rarely be more than one author per section. If there is more than one author, consider the most relevant author.\n\n"
        "**Output Format:**\n"
        "Provide author information in JSON format with the following structure:\n"
        "```json\n"
        "{\n"
        "  \"author\": {\n"
        "    \"name\": \"...\",\n"
        "    \"biography\": \"...\"\n"
        "  }\n"
        "}\n"
        "```\n"
        "**Example Output:**\n"
        "```json\n"
        "{\n"
        "  \"author\": {\n"
        "    \"name\": \"Giulio Tononi\",\n"
        "    \"biography\": \"Giulio Tononi is a neuroscientist and psychiatrist known for his Integrated Information Theory of consciousness.\"\n"
        "  }\n"
        "}\n"
        "```\n"
        "Ensure that your output is valid JSON for further processing."
        "**Important:** Output only the JSON code block as specified above, without any additional text or explanations."
    ),
    llm_config=llm_config,
)


supporting_material_extractor = AssistantAgent(
    name="SupportingMaterialExtractor",
    system_message=(
        "You are responsible for extracting and categorizing references and supporting materials from the text and bibliography.\n\n"
        "**Responsibilities:**\n"
        "- Extract references and supporting materials associated with theories.\n"
        "- **Guideline 1:** A SupportingMaterial is a bibliography entry that is associated with a Theory.\n"
        "- **Guideline 2:** If another author is mentioned in the theory and a reference is attributed to them, associate that SupportingMaterial with the Theory but not with an Author.\n"
        "- **Guideline 3:** Retain every source for each theory, but don't attribute works to Authors incorrectly.\n\n"
        "**Output Format:**\n"
        "Provide the supporting materials in JSON format with the following structure:\n"
        "```json\n"
        "{\n"
        "  \"supporting_materials\": [\n"
        "    {\n"
        "      \"citation\": \"...\",\n"
        "      \"material_type\": \"...\",  // e.g., 'Journal Article', 'Book'\n"
        "      \"associated_theory_name\": \"...\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n"
        "**Example Output:**\n"
        "```json\n"
        "{\n"
        "  \"supporting_materials\": [\n"
        "    {\n"
        "      \"citation\": \"Tononi, G. (2004). An information integration theory of consciousness. BMC Neuroscience, 5, 42.\",\n"
        "      \"material_type\": \"Journal Article\",\n"
        "      \"associated_theory_name\": \"Integrated Information Theory\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n"
        "Ensure that your output is valid JSON for further processing, and include the full bibliography entry in the 'citation' field."
        "**Important:** Output only the JSON code block as specified above, without any additional text or explanations."
    ),
    llm_config=llm_config,
)

# Load your JSON data
with open('sections_with_theorists.json') as file:
    data = json.load(file)

# Load references data
with open('References.txt') as file:
    references = file.readlines()

print("Sample References:", references[5])

# Function to extract citations from text
def extract_citations(text):
    # Find all valid citations in the format (Author, Year)
    citations = re.findall(r'\([A-Za-z]+, \d{4}\)', text)
    # Clean citations by removing any extra spaces
    citations = [citation.strip() for citation in citations]
    print("Extracted Citations:", citations)  # Debug: Print extracted citations
    return citations

# Function to filter references based on citations
def filter_references(citations, references):
    # Prepare a list to hold the filtered references
    filtered_references = []
    # For each citation, find matching references
    for citation in citations:
        # Extract the author's last name from the citation
        match = re.match(r'\((?P<author>[A-Za-z]+), \d{4}\)', citation)
        if match:
            author = match.group('author')
            print(f"Searching for author: {author}")  # Debug: Print author being searched
            # Search for references containing the author's last name
            for i, ref in enumerate(references):
                if author in ref:
                    print(f"Match found for author {author} in reference: {ref}")  # Debug: Print matching reference
                    # Include a few lines before and after the match
                    start = max(i - 2, 0)
                    end = min(i + 3, len(references))
                    filtered_references.extend(references[start:end])
                    filtered_references.append('\n')  # Add a newline for separation
                    break  # Assuming one match per citation
    # Remove duplicates while preserving order
    seen = set()
    filtered_references = [x for x in filtered_references if not (x in seen or seen.add(x))]
    print("Filtered References:", filtered_references)  # Debug: Print filtered references
    return ''.join(filtered_references)

# Define the custom speaker selection function
def custom_speaker_selection_func(last_speaker, groupchat):
    messages = groupchat.messages

    if len(messages) <= 1:
        return theory_summarizer

    if last_speaker == theory_summarizer:
        return author_curator
    elif last_speaker == author_curator:
        return supporting_material_extractor
    elif last_speaker == supporting_material_extractor:
        return None  # End of conversation
    else:
        return None

# Initialize aggregated data structures
aggregated_data = {
    'authors': {},
    'theories': {},
    'categories': {},
    'supporting_materials': []
}

for index, section in enumerate(data):
    # Check if the section has already been processed
    output_file = f'output/section_{index}_log.txt'
    if os.path.exists(output_file):
        print(f"Section {index} already processed. Skipping.")
        continue

    # Set up logging for this section
    logger = logging.getLogger(f'section_{index}')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(output_file)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(fh)

    logger.debug(f"Processing Section {index}")

    # Extract citations and filter references
    section_text = section.get('text', '')
    citations = extract_citations(section_text)
    filtered_references = filter_references(citations, references)

    # Initialize the group chat
    groupchat = GroupChat(
        agents=[theory_summarizer, author_curator, supporting_material_extractor],
        messages=[],
        max_round=10,
        speaker_selection_method=custom_speaker_selection_func,
    )

    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    # Prepare initial message with data
    initial_message = f"""
    Process the following section according to your roles and responsibilities.

    Section Text: {section_text}

    The SupportingMaterialExtractor will need the following:

    Citations: {citations}

    Filtered References:
    {filtered_references}
    """

    with Cache.disk(cache_seed=42) as cache:
        # Initiate the chat
        chat_history = manager.initiate_chat(
            manager,
            message=initial_message,
            cache=cache,
        )

    # Log the chat history
    for msg in manager.groupchat.messages:
        logger.debug(f"{msg['name']}: {msg['content']}")

    # Collect outputs from agents
    theory_output = None
    author_output = None
    supporting_materials_output = None

    for msg in manager.groupchat.messages:
        if msg['name'] == 'TheorySummarizer':
            theory_output = msg['content']
        elif msg['name'] == 'AuthorCurator':
            author_output = msg['content']
        elif msg['name'] == 'SupportingMaterialExtractor':
            supporting_materials_output = msg['content']

    # Parse and aggregate data
    # Use try-except blocks to handle JSON parsing errors
    try:
        theory_json = extract_json_from_output(theory_output)
        if theory_json:
            theory_data = json.loads(theory_json)
            theory = theory_data.get('theory')
            if theory:
                theory_name = theory.get('name')
                if theory_name:
                    # Aggregate theory data
                    if theory_name not in aggregated_data['theories']:
                        aggregated_data['theories'][theory_name] = theory
                    # Aggregate categories
                    categories = theory.get('categories', [])
                    for category_name in categories:
                        if category_name not in aggregated_data['categories']:
                            aggregated_data['categories'][category_name] = {'name': category_name}
        else:
            logger.error("No JSON found in theory output.")
    except Exception as e:
        logger.error(f"Error processing theory output: {e}")

    try:
        author_json = extract_json_from_output(author_output)
        if author_json:
            author_data = json.loads(author_json)
            author = author_data.get('author')
            if author:
                author_name = author.get('name')
                if author_name:
                    if author_name not in aggregated_data['authors']:
                        aggregated_data['authors'][author_name] = author
        else:
            logger.error("No JSON found in author output.")
    except Exception as e:
        logger.error(f"Error processing author output: {e}")

    try:
        theory_json = extract_json_from_output(theory_output)
        if theory_json:
            theory_data = json.loads(theory_json)
            theory = theory_data.get('theory')
            if theory:
                theory_name = theory.get('name')
                if theory_name:
                    # Aggregate theory data
                    # Associate the theory with the author from this section
                    theory['author_name'] = None  # Default to None
                    if author_output:
                        author_json = extract_json_from_output(author_output)
                        if author_json:
                            author_data = json.loads(author_json)
                            author = author_data.get('author')
                            if author:
                                author_name = author.get('name')
                                theory['author_name'] = author_name
                                # Aggregate author data
                                if author_name not in aggregated_data['authors']:
                                    aggregated_data['authors'][author_name] = author
                    # Add theory to aggregated data
                    if theory_name not in aggregated_data['theories']:
                        aggregated_data['theories'][theory_name] = theory
                    else:
                        # Update existing theory with author_name if missing
                        if 'author_name' not in aggregated_data['theories'][theory_name]:
                            aggregated_data['theories'][theory_name]['author_name'] = theory['author_name']
    except Exception as e:
        logger.error(f"Error processing theory or author output: {e}")

    try:
        sm_json = extract_json_from_output(supporting_materials_output)
        if sm_json:
            sm_data = json.loads(sm_json)
            supporting_materials = sm_data.get('supporting_materials', [])
            aggregated_data['supporting_materials'].extend(supporting_materials)
        else:
            logger.error("No JSON found in supporting materials output.")
    except Exception as e:
        logger.error(f"Error processing supporting materials output: {e}")

    # Remove the handler after processing
    logger.removeHandler(fh)

def sanitize_string(s):
    if s is None:
        return ''
    # Escape backslashes first
    s = s.replace('\\', '\\\\')
    # Escape single quotes
    s = s.replace("'", "\\'")
    # Escape double quotes if necessary
    s = s.replace('"', '\\"')
    # Replace newlines and carriage returns with escaped versions
    s = s.replace('\n', '\\n').replace('\r', '\\r')
    return s

def generate_seeds_file(aggregated_data):
    seeds_code = ''

    # Generate authors
    for author_name, author in aggregated_data['authors'].items():
        name = sanitize_string(author['name'])
        biography = sanitize_string(author['biography'])
        seeds_code += f"author = Author.find_or_create_by(name: '{name}') do |a|\n"
        seeds_code += f"  a.biography = '{biography}'\n"
        seeds_code += "end\n\n"

    # Generate categories
    for category_name in aggregated_data['categories'].keys():
        name = sanitize_string(category_name)
        seeds_code += f"category = Category.find_or_create_by(name: '{name}')\n\n"

    # Generate theories and associate with authors and categories
    for theory_name, theory in aggregated_data['theories'].items():
        name = sanitize_string(theory['name'])
        description = sanitize_string(theory['description'])
        seeds_code += f"theory = Theory.find_or_create_by(name: '{name}') do |t|\n"
        seeds_code += f"  t.description = '{description}'\n"
        seeds_code += "end\n\n"

        # Associate with author
        author_name = theory.get('author_name')
        if author_name and author_name in aggregated_data['authors']:
            author_name_sanitized = sanitize_string(author_name)
            seeds_code += f"author = Author.find_by(name: '{author_name_sanitized}')\n"
            seeds_code += f"theory.authors << author unless theory.authors.include?(author)\n\n"

        # Associate with categories
        categories = theory.get('categories', [])
        for category_name in categories:
            category_name_sanitized = sanitize_string(category_name)
            seeds_code += f"category = Category.find_by(name: '{category_name_sanitized}')\n"
            seeds_code += f"theory.categories << category unless theory.categories.include?(category)\n\n"

    # Generate supporting materials and associate with theories
    for material in aggregated_data['supporting_materials']:
        theory_name = material.get('associated_theory_name')
        if theory_name and theory_name in aggregated_data['theories']:
            theory_name_sanitized = sanitize_string(theory_name)
            seeds_code += f"theory = Theory.find_by(name: '{theory_name_sanitized}')\n"
            citation = sanitize_string(material['citation'])
            material_type = sanitize_string(material['material_type'])
            seeds_code += f"supporting_material = SupportingMaterial.find_or_create_by(citation: '{citation}') do |sm|\n"
            seeds_code += f"  sm.material_type = '{material_type}'\n"
            seeds_code += "end\n\n"
            # Associate supporting material with theory
            seeds_code += f"theory.supporting_materials << supporting_material unless theory.supporting_materials.include?(supporting_material)\n\n"

    return seeds_code

seeds_code = generate_seeds_file(aggregated_data)

with open('output/seeds.rb', 'w') as f:
    f.write(seeds_code)

print("Processing complete. Check the output/seeds.rb file for the results.")