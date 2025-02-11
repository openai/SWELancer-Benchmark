import libcst as cst
import sys
from pathlib import Path


class ModifyChromiumLaunchArgs(cst.CSTTransformer):
    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call):
        # Check if the method being called is "chromium.launch"
        if (
            isinstance(original_node.func, cst.Attribute)
            and original_node.func.attr.value == "launch"
        ):
            if (
                isinstance(original_node.func.value.attr, cst.Name)
                and original_node.func.value.attr.value == "chromium"
            ):
                # Extract the existing arguments (slow_mo, if any)
                existing_args = {
                    arg.keyword.value: arg for arg in updated_node.args if arg.keyword
                }
                
                # Get value of existing arguments
                slow_mo_val = cst.Name("None")
                if "slow_mo" in existing_args:
                    slow_mo_val = existing_args["slow_mo"].value
                    
                # Force the channel to be "chromium"
                channel_val = cst.SimpleString(value='"chromium"')

                # Create new or update existing arguments
                new_args = [
                    cst.Arg(
                        value=cst.Dict(
                            elements=[
                                cst.DictElement(
                                    key=cst.SimpleString(
                                        value='"server"',
                                        lpar=[],
                                        rpar=[],
                                    ),
                                    value=cst.SimpleString(
                                        value='"http://localhost:8080"',
                                        lpar=[],
                                        rpar=[],
                                    ),
                                    comma=cst.MaybeSentinel.DEFAULT,
                                    whitespace_before_colon=cst.SimpleWhitespace(
                                        value="",
                                    ),
                                    whitespace_after_colon=cst.SimpleWhitespace(
                                        value=" ",
                                    ),
                                ),
                            ],
                            lbrace=cst.LeftCurlyBrace(
                                whitespace_after=cst.SimpleWhitespace(
                                    value="",
                                ),
                            ),
                            rbrace=cst.RightCurlyBrace(
                                whitespace_before=cst.SimpleWhitespace(
                                    value="",
                                ),
                            ),
                            lpar=[],
                            rpar=[],
                        ),
                        keyword=cst.Name(
                            value="proxy",
                            lpar=[],
                            rpar=[],
                        ),
                        equal=cst.MaybeSentinel.DEFAULT,
                        comma=cst.MaybeSentinel.DEFAULT,
                    ),
                    cst.Arg(keyword=cst.Name("headless"), value=cst.Name("False")),
                    cst.Arg(
                        keyword=cst.Name(value="args"),
                        value=cst.List(
                            elements=[
                                cst.Element(
                                    value=cst.SimpleString(
                                        value='"--no-sandbox"'
                                    ),
                                    comma=cst.MaybeSentinel.DEFAULT,
                                ),
                                cst.Element(
                                    value=cst.SimpleString(
                                        value='"--disable-dev-shm-usage"'
                                    ),
                                    comma=cst.MaybeSentinel.DEFAULT,
                                ),
                                cst.Element(
                                    value=cst.SimpleString(
                                        value='"--ignore-certificate-errors"'
                                    ),
                                    comma=cst.MaybeSentinel.DEFAULT,
                                ),
                                cst.Element(
                                    value=cst.SimpleString(
                                        value='"--disable-web-security"'
                                    ),
                                    comma=cst.MaybeSentinel.DEFAULT,
                                ),
                                cst.Element(
                                    value=cst.SimpleString(
                                        value='"--disable-features=IsolateOrigins,site-per-process"'
                                    ),
                                    comma=cst.MaybeSentinel.DEFAULT,
                                ),
                            ],
                            lbracket=cst.LeftSquareBracket(),
                            rbracket=cst.RightSquareBracket(),
                        ),
                        equal=cst.MaybeSentinel.DEFAULT,
                        comma=cst.MaybeSentinel.DEFAULT,
                    ),
                    cst.Arg(
                        keyword=cst.Name(value="slow_mo"),
                        value=slow_mo_val,
                        comma=cst.MaybeSentinel.DEFAULT,
                    ),
                    cst.Arg(
                        keyword=cst.Name(value="channel"),
                        value=channel_val,
                        comma=cst.MaybeSentinel.DEFAULT,
                    ),
                ]

                # Combine all arguments and replace the call
                updated_args = []
                seen_keywords = set()

                for arg in new_args:
                    if arg.keyword and arg.keyword.value not in seen_keywords:
                        updated_args.append(arg)
                        seen_keywords.add(arg.keyword.value)
                    elif not arg.keyword:
                        updated_args.append(arg)

                return updated_node.with_changes(args=new_args)
        return updated_node


class ModifyNewContextArgs(cst.CSTTransformer):
    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call):
        # Check if the method being called is "new_context"
        if (
            isinstance(original_node.func, cst.Attribute)
            and original_node.func.attr.value == "new_context"
        ):
            # Extract existing arguments into a dictionary
            existing_args = {
                arg.keyword.value: arg for arg in updated_node.args if arg.keyword
            }

            # Define the new argument to add
            new_arg = cst.Arg(keyword=cst.Name("ignore_https_errors"), value=cst.Name("True"))

            # Check if 'ignore_https_errors' is already present
            if "ignore_https_errors" not in existing_args:
                # Add the new argument at the end
                updated_args = updated_node.args + [new_arg]
            else:
                updated_args = updated_node.args  # Keep existing args unchanged

            # Replace the function call's arguments
            return updated_node.with_changes(args=updated_args)

        return updated_node


def modify_file(file_path: str):
    # Read the original file
    with open(file_path, "r") as source:
        code = source.read()

    # Parse the code into a CST tree
    tree = cst.parse_module(code)

    # Apply the first transformer
    transformer1 = ModifyChromiumLaunchArgs()
    modified_tree = tree.visit(transformer1)

    # Write the modified code back to the file
    with open(file_path, "w") as dest:
        dest.write(modified_tree.code)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python rewrite.py <path_to_file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    modify_file(str(file_path))
    sys.exit(0)
