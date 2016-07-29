# GWTParse
A simple application that parses GWT RPC strings and turns them into 
python objects

# Notes
1. The author of this is far too obsessed with functional interfaces. As a
result, they made a lot of deep copys of the data array. All of these
can be removed safely, but you will no longer have a funcitonal
interface.
2. The verbosity specifies exactly how much user interaction should be
needed to run the script:
  * Silent - Any string not specified as a class will be treated as a string
  * Default - The script will make guesses about what is an isn't a string
   and will learn what are classes
  * Verbose - The scirpt won't make any guesses, but will still learn what
   is and isn't a class
  * Very Verbose - The script will ask for user input on any decision

# Contributions
There's a lot to be done with this application, so if you want, please send
a pull request
