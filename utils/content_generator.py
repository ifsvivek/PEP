import os
import json
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config import Config

# Initialize Groq LLM
groq_llm = ChatGroq(api_key=Config.GROQ_API_KEY, model_name="llama-3.3-70b-versatile")


def generate_content(topic):
    """Generate educational content for a given topic"""

    content_prompt = PromptTemplate(
        input_variables=["topic"],
        template="""
        You are an expert educational content creator. Create detailed, comprehensive educational content about {topic}.
        
        Your response MUST be formatted as valid JSON with the following structure:
        {{
            "title": "{topic}",
            "introduction": "A comprehensive introductory paragraph explaining what {topic} is, its significance, and why it matters (minimum 150 words)",
            "sections": [
                {{
                    "heading": "Key Concept 1",
                    "content": "Detailed explanation of this concept with clear descriptions, minimum 200 words",
                    "examples": ["Specific Example 1 with details", "Specific Example 2 with details"]
                }},
                {{
                    "heading": "Key Concept 2", 
                    "content": "Detailed explanation of this concept with clear descriptions, minimum 200 words",
                    "examples": ["Specific Example 1 with details", "Specific Example 2 with details"]
                }},
                {{
                    "heading": "Key Concept 3",
                    "content": "Detailed explanation of this concept with clear descriptions, minimum 200 words",
                    "examples": ["Specific Example 1 with details", "Specific Example 2 with details"]
                }},
                {{
                    "heading": "Applications and Importance",
                    "content": "Explanation of how this topic applies to real-world scenarios and its importance, minimum 150 words",
                    "examples": ["Real-world application 1", "Real-world application 2"]
                }}
            ],
            "summary": "A comprehensive summary of everything covered about {topic}, minimum 150 words",
            "further_reading": ["Specific Resource 1 with author/source", "Specific Resource 2 with author/source", "Specific Resource 3 with author/source"]
        }}
        
        Ensure all content is factually accurate, educational, and engaging. Include sufficient detail in each section.
        Your response must be ONLY the JSON with no additional text or explanations.
        """,
    )

    content_chain = LLMChain(llm=groq_llm, prompt=content_prompt)

    try:
        response = content_chain.run(topic=topic)
        # Clean the response to ensure it's valid JSON
        # Find JSON content between curly braces
        json_str = response.strip()
        if not json_str.startswith("{"):
            start = json_str.find("{")
            if start != -1:
                json_str = json_str[start:]
        if not json_str.endswith("}"):
            end = json_str.rfind("}")
            if end != -1:
                json_str = json_str[: end + 1]

        # Parse response to ensure it's valid JSON
        content = json.loads(json_str)
        return content
    except Exception as e:
        print(f"Error generating content: {e}")
        print(
            f"Response received: {response[:500]}..."
        )  # Print part of the response for debugging

        # Fallback content in case of error
        return {
            "title": topic,
            "introduction": f"Introduction to {topic}: {topic} is a fascinating subject that encompasses various concepts and principles. Understanding {topic} is essential for advancing knowledge in this domain and its related fields.",
            "sections": [
                {
                    "heading": "Overview of " + topic,
                    "content": f"This section provides a basic overview of {topic}, including its fundamental concepts, historical development, and current understanding. {topic} represents an important area of study with significant implications for our understanding of related phenomena.",
                    "examples": [
                        f"Example application of {topic} in a real-world context",
                        f"Historical development of {topic} as a field of study",
                    ],
                },
                {
                    "heading": "Key Principles",
                    "content": f"Several key principles underpin our understanding of {topic}. These principles form the foundation for more advanced concepts and applications in this field. Understanding these fundamental principles is essential for mastering {topic}.",
                    "examples": [
                        "Principle 1 with practical example",
                        "Principle 2 with practical example",
                    ],
                },
                {
                    "heading": "Applications",
                    "content": f"{topic} has numerous applications across various fields. From theoretical implementations to practical uses in everyday scenarios, the concepts of {topic} prove valuable in solving problems and advancing knowledge.",
                    "examples": ["Application in research", "Application in industry"],
                },
            ],
            "summary": f"Summary of {topic}: This module explored the fundamental aspects of {topic}, including its key principles, historical context, and practical applications. By understanding these concepts, learners gain valuable insights into how {topic} influences related fields and contributes to broader knowledge.",
            "further_reading": [
                f"Introduction to {topic} by Academic Press",
                f"Advanced {topic}: Theory and Practice",
                f"{topic} in the Modern World: Current Research and Future Directions",
            ],
        }


def generate_quiz(content):
    """Generate quiz questions based on the content"""
    
    quiz_prompt = PromptTemplate(
        input_variables=["content"],
        template="""
        Based on the following educational content, create 5 multiple-choice questions for a quiz. The questions should test understanding of key concepts and facts from the content. Each question must have exactly 4 options with only one correct answer.

        CONTENT:
        {content}
        
        Your response MUST be a valid JSON object with this exact structure:
        {{
            "topic": "Topic Name",
            "questions": [
                {{
                    "question": "A clear, specific question based on the content?",
                    "options": [
                        "A specific, plausible answer choice",
                        "Another specific, plausible answer choice",
                        "Another specific, plausible answer choice",
                        "Another specific, plausible answer choice"
                    ],
                    "correct": "The exact text of the correct answer from options"
                }}
            ]
        }}

        Make sure:
        1. Questions are specific and test actual understanding
        2. All options are plausible and relevant
        3. Questions cover different aspects of the content
        4. Language is clear and unambiguous
        5. The correct answer is exactly matched with one of the options
        
        Return ONLY the JSON with no additional text.
        """
    )

    quiz_chain = LLMChain(llm=groq_llm, prompt=quiz_prompt)

    try:
        response = quiz_chain.run(content=json.dumps(content))
        # Clean and parse JSON response
        json_str = response.strip()
        if not json_str.startswith("{"):
            start = json_str.find("{")
            if start != -1:
                json_str = json_str[start:]
        if not json_str.endswith("}"):
            end = json_str.rfind("}")
            if end != -1:
                json_str = json_str[:end + 1]

        quiz_data = json.loads(json_str)
        
        # Validate quiz structure
        if not quiz_data.get("questions"):
            raise ValueError("No questions generated")
            
        return quiz_data
        
    except Exception as e:
        print(f"Error generating quiz: {e}")
        # Return fallback quiz with content-specific question
        return {
            "topic": content.get("title", "Topic"),
            "questions": [
                {
                    "question": f"What is the main focus of {content.get('title', 'this topic')}?",
                    "options": [
                        content.get("introduction", "").split('.')[0],
                        "An incorrect but plausible answer",
                        "Another incorrect but plausible answer",
                        "Yet another incorrect but plausible answer"
                    ],
                    "correct": content.get("introduction", "").split('.')[0]
                }
            ]
        }
