from autogen import SwarmResult
from typing import Literal
import os
import re
import ast
from autogen.cmbagent_utils import cmbagent_debug
from IPython.display import Image as IPImage, display as ip_display
from autogen.cmbagent_utils import IMG_WIDTH


def register_functions_to_agents(cmbagent_instance):
    '''
    This function registers the functions to the agents.
    '''
    planner = cmbagent_instance.get_agent_from_name('planner')
    planner_response_formatter = cmbagent_instance.get_agent_from_name('planner_response_formatter')
    plan_recorder = cmbagent_instance.get_agent_from_name('plan_recorder')
    plan_reviewer = cmbagent_instance.get_agent_from_name('plan_reviewer')
    reviewer_response_formatter = cmbagent_instance.get_agent_from_name('reviewer_response_formatter')
    review_recorder = cmbagent_instance.get_agent_from_name('review_recorder')
    researcher = cmbagent_instance.get_agent_from_name('researcher')
    researcher_response_formatter = cmbagent_instance.get_agent_from_name('researcher_response_formatter')
    engineer = cmbagent_instance.get_agent_from_name('engineer')
    engineer_response_formatter = cmbagent_instance.get_agent_from_name('engineer_response_formatter')
    classy_sz = cmbagent_instance.get_agent_from_name('classy_sz_agent')
    classy_sz_response_formatter = cmbagent_instance.get_agent_from_name('classy_sz_response_formatter')
    executor = cmbagent_instance.get_agent_from_name('executor')
    control = cmbagent_instance.get_agent_from_name('control')
    admin = cmbagent_instance.get_agent_from_name('admin')




    def record_plan(plan_suggestion: str, number_of_steps_in_plan: int, context_variables: dict) -> SwarmResult:
        """
        Records a suggested plan and updates relevant execution context.

        This function logs a full plan suggestion into the `context_variables` dictionary. If no feedback 
        remains to be given (i.e., `context_variables["feedback_left"] == 0`), the most recent plan 
        suggestion is marked as the final plan. The function also updates the total number of steps in 
        the plan.

        The function ensures that the plan is properly stored and transferred to the `plan_reviewer` agent 
        for further evaluation.

        Args:
            plan_suggestion (str): The complete plan suggestion to be recorded.
            number_of_steps_in_plan (int): The total number of **Steps** in the suggested plan.
            context_variables (dict): A dictionary maintaining execution context, including previous plans, 
                feedback tracking, and finalized plans.
        """
        context_variables["plans"].append(plan_suggestion)

        context_variables["proposed_plan"] = plan_suggestion

        context_variables["number_of_steps_in_plan"] = number_of_steps_in_plan

        if context_variables["feedback_left"]==0:
            context_variables["final_plan"] = context_variables["plans"][-1]
            return SwarmResult(agent=control, ## transfer to control
                            values="Planning stage complete. Switching to control.",
                            context_variables=context_variables)
        else:
            return SwarmResult(agent=plan_reviewer, ## transfer to plan reviewer
                            values="Plan has been logged.",
                            context_variables=context_variables)


    plan_recorder._add_single_function(record_plan)



    def record_review(plan_review: str, context_variables: dict) -> SwarmResult:
        """ Record reviews of the plan."""
        context_variables["reviews"].append(plan_review)
        context_variables["feedback_left"] -= 1

        context_variables["recommendations"] = plan_review

        # if context_variables["feedback_left"]


        # Controlling the flow to the next agent from a tool call
        # if context_variables["reviews_left"] < 0:
        #     context_variables["plan_recorded"] = True
        #     return SwarmResult(agent=plan_manager,
        #                        values="No further recommendations to be made on the plan. Update plan and proceed",
        #                        context_variables=context_variables)
        # else:
        return SwarmResult(agent=planner,  ## transfer back to planner
                        values=f"""
Recommendations have been logged.  
Number of feedback rounds left: {context_variables["feedback_left"]}. 
Now, update the plan accordingly, planner!""",
                        
                        context_variables=context_variables)


    review_recorder._add_single_function(record_review)


    def record_status(
        current_status: Literal["in progress", "failed", "completed"],
        current_plan_step_number: int,
        current_sub_task: str,
        current_instructions: str,
        agent_for_sub_task: str,
        context_variables: dict
    ) -> SwarmResult:
        """
        Updates the execution context and returns the current progress.
        Must be called **before calling the agent in charge of the next sub-task**.
        Must be called **after** each action taken.

        Args:
            current_status (str): The current status ("in progress", "failed", or "completed").
            current_plan_step_number (int): The current step number in the plan.
            current_sub_task (str): Description of the current sub-task.
            current_instructions (str): Instructions for the sub-task.
            agent_for_sub_task (str): The agent responsible for the sub-task.
            context_variables (dict): Execution context dictionary.

        Returns:
            SwarmResult: Contains a formatted status message and updated context.
        """
    

        # Map statuses to icons
        status_icons = {
            "completed": "✅",
            "failed": "❌",
            "in progress": "⏳"  # or any other icon you prefer
        }
        
        icon = status_icons.get(current_status, "")
        
        context_variables["current_plan_step_number"] = current_plan_step_number
        context_variables["current_sub_task"] = current_sub_task
        context_variables["agent_for_sub_task"] = agent_for_sub_task
        context_variables["current_instructions"] = current_instructions
        context_variables["current_status"] = current_status

        codes = os.path.join(cmbagent_instance.work_dir, context_variables['codebase_path'])
        docstrings = load_docstrings(codes)
        output_str = ""
        for module, info in docstrings.items():
            output_str += "-----------\n"
            output_str += f"Filename: {module}.py\n"
            output_str += f"File path: {info['file_path']}\n\n"
            output_str += f"Available functions:\n"
            for func, doc in info['functions'].items():
                output_str += f"function name: {func}\n"
                output_str += "````\n"
                output_str += f"{doc}\n"
                output_str += "````\n\n"

        # Store the full output string in your context variable.
        context_variables["current_codebase"] = output_str

        # Load image plots from the "data" directory.
        data_directory = os.path.join(cmbagent_instance.work_dir, context_variables['database_path'])
        image_files = load_plots(data_directory)
 
        # Retrieve the list of images that have been displayed so far.
        displayed_images = context_variables.get("displayed_images", [])

        # Identify new images that haven't been displayed before.
        new_images = [img for img in image_files if img not in displayed_images]

        # Display only the new images.
        for img_file in new_images:
            ip_display(IPImage(filename=img_file, width=2 * IMG_WIDTH))

        # Update the context to include the newly displayed images.
        context_variables["displayed_images"] = displayed_images + new_images

        
        if cmbagent_debug:
            print("\n\n in functions.py record_status: context_variables: ", context_variables)


        return SwarmResult(
            values=f"""
**Step number:** {context_variables["current_plan_step_number"]} out of {context_variables["number_of_steps_in_plan"]}.\n 
**Sub-task:** {context_variables["current_sub_task"]}\n 
**Agent in charge of sub-task:** `{context_variables["agent_for_sub_task"]}`\n 
**Instructions:**\n 
{context_variables["current_instructions"]}\n 
**Status:** {context_variables["current_status"]} {icon}
    """,
            context_variables=context_variables)
    
    control._add_single_function(record_status)



def extract_file_path_from_source(source):
    """
    Extracts the file path from the top comment in the source code.
    Expects a line like: "# filename: codebase/module.py"
    
    Parameters:
        source (str): The source code of the file.
        
    Returns:
        str or None: The file path if found, else None.
    """
    match = re.search(r'^#\s*filename:\s*(.+)$', source, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None

def extract_functions_docstrings_from_file(file_path):
    """
    Parses the given Python file and extracts docstrings from all top-level function
    definitions (including methods in classes) without capturing nested (internal) functions.
    Also extracts the file path from the file's top comment.
    
    Parameters:
        file_path (str): Path to the Python file.
    
    Returns:
        dict: A dictionary with two keys:
              - "file_path": the file path extracted from the comment.
              - "functions": a dictionary mapping function names to their docstrings.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
        
    # Extract the file path from the comment at the top of the file
    file_path_from_comment = extract_file_path_from_source(source)
    
    # Parse the AST
    tree = ast.parse(source, filename=file_path)
    functions = {}
    
    # Process only top-level statements
    for node in tree.body:
        # Capture top-level function definitions.
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = ast.get_docstring(node)
        # Optionally, capture methods inside classes.
        elif isinstance(node, ast.ClassDef):
            for subnode in node.body:
                if isinstance(subnode, ast.FunctionDef):
                    qualified_name = f"{node.name}.{subnode.name}"
                    functions[qualified_name] = ast.get_docstring(subnode)
                    
    return {"file_path": file_path_from_comment, "functions": functions}

def load_docstrings(directory="codebase"):
    """
    Loads all top-level function docstrings from Python files in the specified directory
    without executing any code, and extracts the file path from the top comment of each file.
    
    Parameters:
        directory (str): Path to the directory containing Python files.
    
    Returns:
        dict: A dictionary where each key is a module name and each value is a dictionary
              containing the file path and another dictionary mapping function names to their docstrings.
    """
    all_docstrings = {}
    
    for file in os.listdir(directory):
        if file.endswith(".py") and not file.startswith("__"):
            module_name = file[:-3]  # Remove the .py extension
            file_path = os.path.join(directory, file)
            doc_info = extract_functions_docstrings_from_file(file_path)
            all_docstrings[module_name] = doc_info
    return all_docstrings



def load_plots(directory: str) -> list:
    """
    Searches the given directory for image files with extensions
    png, jpg, jpeg, or gif and returns a list of their file paths.
    
    Args:
        directory (str): The directory to search.
        
    Returns:
        list: List of image file paths.
    """
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif')
    image_files = []
    if os.path.exists(directory):
        for file in os.listdir(directory):
            if file.lower().endswith(image_extensions):
                image_files.append(os.path.join(directory, file))
    return image_files