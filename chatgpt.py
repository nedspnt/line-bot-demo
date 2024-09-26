import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

# load environment varaibles from .env file
load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY_LINE"))

# conversation memory
memory = ConversationBufferMemory()
llm = ChatOpenAI(temperature=0, openai_api_key=os.getenv('OPENAI_API_KEY_LINE'))
conversation = ConversationChain(llm=llm, memory=memory)

contexts = dict()

inventory_table = "inventory_all_branches"
promotion_table = "promotion_all_branches"

contexts["customer_admin"] = f"""
    You are a Line admin for a convenient store. 
    You are responsible for answering questions from customers. 
    Given the user text in the chat, you will have to classify their intent into one of these classes:
    (1) promotion inquiry
    (2) remaining inventory inquiry
    (3) Other intents

    You will reply only intent class, and here is your example of how to response to questions:
    
    Question: Do you still have product P004?
    Your answer: 2

    Question: What is today promotion for product P004?
    Your answer: 1

    Question: Hello, store manager!
    Your answer: 3

    Question: For product Fab, do you have a promotion?
    Your answer: 1
    """

contexts["database_admin"] = f"""
    You are a database administrator as well as store manager. 
    You take care of 2 tables: {inventory_table} and {promotion_table}.
    
    [1] {inventory_table} table has 4 columns: datetime, branch_id, product_id, remaining_inventory.
    [2] {promotion_table} table has 3 columns: datetime, branch_id, promotion_id, product_id, promo_details 
    
    You are an expert in SQL, generating queries to users who requested data.

    You will be chating with your customers, who want to either (1) inventory or (2) promotion before they come to the store.
    Once you read your customer request, you understand the intent category it belongs to.

    For example, when a user asked about the remaining inventory for product_id P001 at branch_id B007, the following query will be used.
    ```
    SELECT * FROM {inventory_table}
    WHERE product_id = 'P001' AND branch_id = 'B007'
    LIMIT 1 
    ``` 

    While a customer is asking for a promotion related to product P003 branch B004, you assume it's today's promotion and you can generate the following example query:
    ```
    SELECT * FROM {promotion_table}
    WHERE product_id = 'P003' AND branch_id = 'B004'
    LIMIT 1 
    ```

    For keyword related to promotion whether it's in Thai, such โปรโมชั่น, โปร, or in English such as promo, we can safely asssume it's promotion inquiry.
    If you can't initially find a product name inside customer's text, look for the word before 'มีโปร'. For example, in the text "แฟ้บมีโปรโมชั่นมั้ยครับ", you may assume the word "แฟ้บ" as a product name. 

    For all answers that are SQL queries, remember that you give them only a query. Do not add other texts, as user will copy your query and run in their db engine.
    In case users ask for something else, simply reply as if you're a store manager of that particular branch.
    """

def augment_prompt(context_role, user_question, branch_id="B001"):
    augmented_prompts = [
            {"role": "system", "content": contexts[context_role]},
            {"role": "assistant", "content": f"We are now in branch {branch_id}. So when a user ask for a product, let's use branch_id = {branch_id} in the query."},
            {"role": "user", "content": user_question}
    ]

    return augmented_prompts

def get_answers(augmented_prompts):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=augmented_prompts
    )
    answers = completion.choices[0].message.content

    return answers 

def reply_conversation(input_message):
    reply = conversation.run(input_message)
    return reply