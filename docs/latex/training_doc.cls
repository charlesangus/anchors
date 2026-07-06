% training document template

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{trainingDoc}


% Load the Base Class
\LoadClassWithOptions{scrartcl}

% Begin Requirements
\RequirePackage{ifthen}

% set font encoding for PDFLaTeX, XeLaTeX, or LuaTeX
\usepackage{ifxetex,ifluatex}
\if\ifxetex T\else\ifluatex T\else F\fi\fi T%
  \usepackage{fontspec}
\else
  \usepackage[T1]{fontenc}
  \usepackage[utf8]{inputenc}
  \usepackage{lmodern}
\fi

% Set the Paper Size and margins
\RequirePackage{geometry}
\geometry{margin=1.0in}

\RequirePackage{needspace}

\RequirePackage{float}

\RequirePackage{caption}
\RequirePackage{subcaption}
\RequirePackage[section]{placeins}

\RequirePackage{graphicx}

\RequirePackage{amsmath}

% quotes in italics
\RequirePackage{etoolbox}
\AtBeginEnvironment{quote}{\itshape}

% set up headers
\RequirePackage{fancyhdr}
\pagestyle{fancy}
\renewcommand{\headrulewidth}{0pt}
\lhead{\@author}
\rhead{\@title}

% tighten list formatting - Pandoc's tightlist doesn't quite work
\RequirePackage{enumitem}
\setlist{nosep}

% Add Department Command
\def\@department{\relax}
\newcommand{\department}[1]{\gdef\@department{#1}}

% needed for squarepipe, used as alt l3 list item ident
\usepackage{amssymb}

% KOMA Options
\KOMAoptions{}
% \setcounter{secnumdepth}{0}
\addtokomafont{disposition}{\rmfamily}
\addtokomafont{disposition}{\mdseries}
\addtokomafont{descriptionlabel}{\rmfamily\scshape}
\renewcommand\labelitemii{$\circ$}
% untested, but should be a hollow square
\renewcommand\labelitemiii{\tiny$\square$}
\addtokomafont{paragraph}{\rmfamily\scshape}

% use small caps for emphasis, and italic for strong
\let\textitold\textit
\let\emphold\emph
\renewcommand{\emph}{\textsc}
\renewcommand{\textit}{\textsc}
\renewcommand{\textbf}{\textitold}

% Custom Title
\renewcommand{\maketitle}{
\noindent
\begin{minipage}[c]{0.2\textwidth}
  \vspace{0pt}
  \begin{center}
    \includegraphics[width=\textwidth]{logo}
  \end{center}
\end{minipage}\hfill%
\begin{minipage}[c]{0.75\textwidth}
  \vspace{0pt}
  {\huge \@title \par}
  \medskip
  {\large \@department\hspace{.5em}\textperiodcentered\hspace{.5em}\@author}
  \vfill
\end{minipage}\hfill
\vspace{2\baselineskip}
\thispagestyle{plain}
}

% required for PanDoc
\providecommand{\tightlist}{}

% how deep to go in toc
\setcounter{tocdepth}{3}

% keep subsection headings with their text
\let\oldsection\section
\renewcommand{\section}{\needspace{5\baselineskip}\oldsection}
\let\oldparagraph\paragraph
\let\oldsubsection\subsection
\renewcommand{\subsection}{\needspace{5\baselineskip}\oldsubsection}
\let\oldparagraph\paragraph
\renewcommand{\paragraph}{\needspace{3\baselineskip}\oldparagraph}

\newcommand\sbullet[1][.5]{\mathbin{\vcenter{\hbox{\scalebox{#1}{$\bullet$}}}}}

% enable "max width=" in graphcis

\usepackage[export]{adjustbox}
