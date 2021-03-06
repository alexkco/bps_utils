import subprocess
import sys
from preprocess import MetaTag

XELATEX_PREAMBLE0 = r'''
%!TEX TS-program = xelatex
%!TEX encoding = UTF-8 Unicode
\documentclass[9pt]{extarticle}
\usepackage{xltxtra,fontspec,xunicode}
\usepackage[a4paper,includefoot,left=0.8in,right=0.5in,top=0.3in,bottom=0.2in,footskip=.1in]{geometry}
\usepackage{fancyhdr}
\usepackage[russian,english]{babel}
\usepackage[usenames,dvipsnames,svgnames]{xcolor}
\usepackage{etoolbox}
\usepackage[hidelinks, bookmarks=true, unicode=true]{hyperref}
\usepackage[normalem]{ulem}
\usepackage{fancyvrb}
\DefineShortVerb{\|}
\makeatletter
\preto{\@verbatim}{\topsep=0pt \partopsep=0pt }
\makeatother
\setlength{\parindent}{0in}

\newcommand\invisiblesection[1]{%
  \refstepcounter{section}%
  \addcontentsline{toc}{section}{\protect\numberline{\thesection}#1}%
  \sectionmark{#1}}


\setmonofont{Lucida Console}
\setromanfont{Lucida Console}
\setlength{\fboxsep}{2pt}
\fancypagestyle{plain}{%
\fancyhf{} % clear all header and footer fields
'''.splitlines(True)


XELATEX_FOOTER = '''\\fancyfoot[C]{{\\fontsize{{11}}{{11}}\\selectfont {0} \\thepage}} % except the center\n'''


XELATEX_PREAMBLE1 = r'''
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}}
\pagestyle{plain}

\begin{document}
{\fontsize{9pt}{10.5pt}\selectfont
'''.splitlines(True)


XELATEX_PAGE_DELIMETER = "\\newpage\n"
XELATEX_LINE = u'''\\verb|{0}|\\\\\n'''

XELATEX_INVERT_COLORS = u'''\\verb|{0}|\\hspace{{- \\fboxsep}}\\colorbox{{black}}{{\\color{{white}}{1}}}\\hspace{{- \\fboxsep}}'''
XELATEX_UNDERLINE = '''\\verb|{0}|\\SaveVerb{{UnderlinedVerb}}|{1}|\\uline{{\\UseVerb{{UnderlinedVerb}}}}'''
XELATEX_LARGE_FONT = '''\\verb|{0}|{{\\Large {1}}}'''


XELATEX_BOOKMARK_SECTION = "\\invisiblesection{{{0}}}\n"
XELATEX_RESET_PAGE_NUMBER = r"\setcounter{page}{1}" + '\n'


XELATEX_EOF = r"\clearpage}\end{document}" + "\n"


_REQUIRED_PACKAGES = ('extsizes', 'l3packages', 'l3kernel', 'tipa', 'ulem',
    'xetex-def', 'realscripts', 'metalogo', 'fancyhdr', 'xcolor', 'etoolbox',
    'fancyvrb', 'hyperref')


class MikTexException(Exception):
    def __init__(self, message, stdout, stderr):

        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, message)

        self.stdout = stdout
        self.stderr = stderr

        
def _tex_escape(line):
    return line.replace('%', '\\%').replace('_', '\\_')


def init_xelatex_src():
    return XELATEX_PREAMBLE0 + XELATEX_PREAMBLE1


def update_xelatex_src(src, code, lines, metadata, calc_type, is_last=False):
    src += [XELATEX_FOOTER.format(_tex_escape(code + ' ' + calc_type)),
            XELATEX_BOOKMARK_SECTION.format(_tex_escape(calc_type)),
            XELATEX_RESET_PAGE_NUMBER]
    
    for i, l in enumerate(lines):
        meta = metadata.get(i, [])
        a = True
        new_l = ""
        cur_offset = 0
        l = l.rstrip('\n')
        # Metadata for one line go in column ascending order
        for (start, length, tag) in meta:
            end = start + length
            # Note: one line can be changed multiple times
            if tag == MetaTag.NEW_PAGE and i != 0: # Ignore 1st line new page tag
                src.append(XELATEX_PAGE_DELIMETER)
            elif tag == MetaTag.REMOVE_LINE:
                a = False
            elif tag == MetaTag.INVERT_COLORS:
                es = _tex_escape(l[start:end])
                new_l += XELATEX_INVERT_COLORS.format(l[cur_offset:start], es)
                cur_offset = end
            elif tag == MetaTag.UNDERLINE:
                new_l += XELATEX_UNDERLINE.format(l[cur_offset:start], l[start:end])
                cur_offset = end
            elif tag == MetaTag.LARGE_FONT:
                es = _tex_escape(l[start:end])
                new_l += XELATEX_LARGE_FONT.format(l[cur_offset:start], es)
                cur_offset = end
        if cur_offset < len(l):
            new_l += XELATEX_LINE.format(l[cur_offset:])
        if cur_offset == len(l):
            new_l += '\\\\\n'
        if a:
            src.append(new_l)
    if is_last:
        src.append(XELATEX_EOF)
    else:
        src.append(XELATEX_PAGE_DELIMETER)


def _call_cmd(cmd_list):
    p = subprocess.Popen(cmd_list,
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    code = p.returncode
    return (code, out, err)

    
def compile_xelatex(tex_fname, pdf_folder, temp_folder):
    (code, out, err) = _call_cmd(['xelatex', '-interaction=nonstopmode',
        '-output-directory', pdf_folder, '-aux-directory', temp_folder, tex_fname])
    if code != 0:
        raise MikTexException('Failed to execute xelatex for file "%s"\n.' %
            tex_fname, out, err)
    (code, out, err) = _call_cmd(['xelatex', '-interaction=nonstopmode',
        '-output-directory', pdf_folder, '-aux-directory', temp_folder, tex_fname])
    if code != 0:
        raise MikTexException('Failed to execute xelatex (second time) for file "%s"\n.' %
            tex_fname, out, err)

        
def preinstall_packages():
    sys.stdout.write('Checking installed MikTex packages...\n')
    (code, out, err) = _call_cmd(['mpm', '--list'])
    if code != 0:
        raise MikTexException('Failed to call Miktex package manager.\n', out, err)
    installed_packages = [l.strip().split()[-1] for l in out.split('\n') if l.strip() and l.split()[0] == 'i']
    
    for p in _REQUIRED_PACKAGES:
        if not p in installed_packages:
            sys.stdout.write('Installing package "%s"...\n' % p)
            (code, out, err) = _call_cmd(['mpm', '--install', p])
            if code != 0:
                raise MikTexException('Failed to install package "%s".\n' % p, out, err)
    sys.stdout.write('All required MikTex packages installed.\n')
    
    
def _test():
    src = start_xelatex_src("1", [["hello\n", "world\n"], ["bye\n", "world\n"]])
    update_xelatex_src(src, "2", [["hello\n", "world\n"], ["bye\n", "world\n"]], is_last=True)
    sys.stdout.writelines(src)
