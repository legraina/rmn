import os
import argparse
import sys
import glob

parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

from process_copy import config


parser = argparse.ArgumentParser(description='Move the copy to moodle folders.',
                                 formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('path', type=str, help='path to the folder where the copies are or will be.')
parser.add_argument('-i', '--import', default=False, action='store_true', dest='import_files',
                    help="Import files from moodle directories or matricules.csv (generated by --find).\n"
                         "Usage to import moodle directories to the folder (all): "
                         "all -r '/root/path' -i -na Devoir1 -co MTH1102 -se H22 -fp tex/front_page.tex.\n"
                         "Usage to import from matricules.csv to the folder (all): "
                         "all -r '/root/path' -i -na Intra -co MTH1102 -se H22 --grades Notes*")
parser.add_argument('-e', '--export', default=False, action='store_true',
                    help="Export files in the copies folder to a directory having the moodle structure. "
                         "Need an existing structure or a grades file. Usage to export from 'all' to 'moodle':\n"
                         "all -e -r '/root/path' -m moodle --grades notes.csv")
parser.add_argument('-f', '--find', type=str,
                    help="Find matricule in files according to the configuration provided and "
                         "store them in matricules.csv.\n"
                         "Use moodle grade csv files to check the existence of a matricule if provided.\n"
                         "Need to define the boxes where to search for a matricule in config.py: "
                         "need a box for the front page and for a regular page.\n"
                         "Usage to find the matricule on every copy in the folder 'all':\n"
                         "all -r '/root/path' -f intra --grades notes*.csv\n"
                         "Here the current configurations available:\n"
                         "%s" % "\n".join(["  - \"%s\": %s" % (k, str(v))
                                           for k, v in config.matricule_box.items()]))
parser.add_argument('-g', '--grade', type=str,
                    help="Read the grade on the first page of the pdf according to the configuration provided.\n"
                         "Need to define the box where to search for grades in config.py.\n"
                         "Usage to grade all copies in 'all' with the configuration 'devoir': "
                         "-r '/root/path' --grades notes.csv -g devoir all\n"
                         "Here the current configurations available:\n"
                         "%s" % "\n".join(["  - \"%s\": %s" % (k, str(v)) for k, v in config.grade_box.items()]))
parser.add_argument('--grades', type=str,
                    help="Path to a csv file to add the grades or a folder containing some csv files or "
                         "a list of files/folders separated by a comma. "
                         "Needs columns \"Matricule\" and \"Note\".")
parser.add_argument('-c', '--compare', default=False, action='store_true',
                    help="Compare grades found to the ones in the file provided in the member grades.")
parser.add_argument("-b", "--batch", type=int, default=500,
                    help="Compress files by batches of the given size in Mb. Default: 500 Mb.")
parser.add_argument('-m', '--mpath', type=str,
                    help='path to the moodle folders or the matricule files generated by find matricule. '
                         'Default: moodle or matricules.csv if --grades used')
parser.add_argument('-r', '--root', type=str, help='root path to add to all input paths')
parser.add_argument("-s", "--suffix", type=str,
                    help="Replace file name by this value when importing. "
                         "Default: {course}_{session}_{name} when any of them are defined.")
parser.add_argument("-fp", "--frontpage", type=str,
                    help="Use the given latex file, fill it with the name and matricule, "
                         "then add it as a front page.")
parser.add_argument("-na", "--name", type=str, help="Name of the devoir or exam.")
parser.add_argument("-co", "--course", type=str, help="Name of the course.")
parser.add_argument("-se", "--session", type=str, help="Name of the session.")

parser.add_argument('-t', '--train', default=False, action='store_true', help='train the CNN on the MNIST dataset')

parser.add_argument('-j', '--job_id', type=str, help='Id of the job.')

parser.add_argument('-u', '--user_id', type=str, help='Id of the user.')
parser.add_argument('-v', '--template_id', type=str, help='Id of the template to use.')


def check_path(path):
    if '*' in path:
        return glob.glob(path)
    return os.path.exists(path)


def try_alternative_root_paths(path, root=None, check=True):
    if not path:
        return []

    if path.startswith('/'):
        if not check:
            return [path]
        return glob.glob(path)

    if root:
        npath = os.path.join(root, path)
        # if file exist, return new path
        if not check:
            return [npath]

        npaths = glob.glob(npath)
        if npaths:
            return npaths

    # try path as a relative path
    npath = os.path.abspath(path)
    # if file doesn't exist throw an error
    if check:
        npaths = glob.glob(npath)
        if npaths:
            return npaths
        raise ValueError('Path %s does not exist.' % path)

    return [npath]


def try_alternative_root_path(path, root=None, check=True):
    npaths = try_alternative_root_paths(path, root, check)
    if len(npaths) > 1:
        raise ValueError("There are several possible paths for "+path)
    return npaths[0] if npaths else None


def run_args(args):
    if args.root:
        args.root = os.path.abspath(args.root)
        if not os.path.exists(args.root):
            raise ValueError('Root path %s does not exist.' % args.root)

    args.path = try_alternative_root_paths(args.path, args.root, check=not args.import_files)
    if args.path:
        print('Path: ', args.path)
    if not args.mpath:
        args.mpath = 'matricules.csv' if args.grades and (args.find or args.import_files) else 'moodle'
    args.mpath = try_alternative_root_path(args.mpath, args.root, check=args.import_files)
    if args.mpath:
        print('Moodle path: '+args.mpath)
    args.frontpage = try_alternative_root_path(args.frontpage, args.root)
    if args.frontpage:
        print('Front page latex file: '+args.frontpage)
    # fetch all the csv files provided in the input for the grades
    grades = []
    if args.grades:
        for g in args.grades.split(','):
            gpaths = try_alternative_root_paths(g, args.root)
            for gpath in gpaths:
                if os.path.isdir(gpath):
                    for f in os.listdir(gpath):
                        if f.endswith('.csv'):
                            grades.append(os.path.join(gpath, f))
                elif gpath.endswith('.csv'):
                    grades.append(gpath)

        if grades:
            print('Grades csv files:')
            for g in grades:
                print('    '+g)
    args.grades = grades

    l_input = ''
    suffix = ''
    if args.course:
        l_input += '\\renewcommand{\\cours}{%s}\n' % args.course
        suffix += '%s_' % args.course
    if args.session:
        l_input += '\\renewcommand{\\session}{%s}\n' % args.session
        suffix += '%s_' % args.session
    if args.name:
        l_input += '\\renewcommand{\\devoir}{%s}\n' % args.name
        suffix += args.name
    config.Latex.input_content += l_input
    if args.suffix is None and suffix:
        args.suffix = suffix

    if args.train:
        print('Training recognition deep learning model')
        from process_copy.train import train
        train()

    if args.find:
        print('Find the matricule for the pdf files in %s' % args.path)
        from process_copy.recognize import find_matricules
        find_matricules(args.path, config.matricule_box[args.find], args.grades)

    if args.import_files:
        print('Import the pdf files from %s to %s' % (args.mpath, args.path))
        from process_copy import mcc
        if args.mpath.endswith('.csv'):
            mcc.import_files_with_csv(args.path, args.mpath, args.grades,
                                      suffix=args.suffix, latex_front_page=args.frontpage)
        else:
            mcc.import_files(args.path, args.mpath, suffix=args.suffix, latex_front_page=args.frontpage)

    if args.grade:
        print('Find the grade for the pdf files in %s' % args.path)
        from process_copy.recognize import grade_all, compare_all
        try:
            if args.compare:
                compare_all(args.path, args.grades, config.grade_box[args.grade])
            else:
                grade_all(args.path, args.grades, config.matricule_box["exam"], args.job_id, args.user_id, args.template_id)
        except KeyError:
            raise KeyError("Grade configuration %s hasn't any configuration defined in config.py" % args.grade)

    if args.export:
        try:
            print('Export the pdf files from %s to %s' % (args.path, args.mpath))
            from process_copy import mcc
            names = mcc.copy_files_for_moodle(args.path, args.mpath, args.grades)
            if names:
                for n in names:
                    ar = try_alternative_root_path(n, args.root, check=False)
                    mcc.zipdirbatch(os.path.join(args.mpath, n), archive=ar, batch=args.batch)
            else:
                mcc.zipdirbatch(args.mpath, archive=args.mpath, batch=args.batch)
        except Exception as e:
            print(e)
            raise


def parse_run_args(args):
    args = parser.parse_args(args)
    run_args(args)
