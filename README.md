# Pandoctor
## An Alfred GUI for Pandoc

,,pd is a relatively simple, easy-to-use way to bring the high-powered functionality of `[Pandoc](http://johnmacfarlane.net/pandoc/)` to you. For those new to ,,p, ,,p is "the universal document converter". It is an amazingly powerful utility that allows you to convert structured text from a ton of possible input formats to an even larger number of output formats. 

![]()

A potential downside to ,,p, however, for many users is that it is entirely a command line utility. This means, on the Mac, you *have to* open Terminal to use it. For many Mac/Alfred users, this is at least slightly daunting. Yet I believe that this should not be a deterrent to more people coming to use the power of ,,p. This is the reason for ,,pd. Now, Alfred users can enjoy the comfortability and familiarity of the Alfred interface to manage ,,p. Here's how:

,,pd is accessed via [File Actions](http://support.alfredapp.com/workflows:config:triggers-file-action). The basic file action is "New Pandoc Conversion", which will kick off a series of interactive Alfred menus to create your ,,p conversion. Once you have chosen the file you want to convert and selected the file action, ,,pd works in 4 stages:

1. specify the text format of the chosen file
2. chose the output format you want for the converted file
3. chose any options you want for the conversion process
4. run ,,p to convert the input file using your chosen options

Luckily, ,,pd is built to move you through these four steps seamlessly and without any interaction on your part aside from selecting and setting the formats and options you want. 

^^^
pd: `Pandoctor`
p: `Pandoc`
^^^