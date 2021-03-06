from __future__ import print_function, division
import os, sys
import stat
import multiprocessing as mp
import subprocess as sp
import socket
import shutil
from datetime import datetime
import numpy as np
import pandas as pd
pd.options.display.max_colwidth = 100

import pyemu

#formatters
#SFMT = lambda x: "{0:>20s}".format(str(x.decode()))
def SFMT(item):
    try:
        s = "{0:>20s}".format(item.decode())
    except:
        s = "{0:>20s}".format(str(item))
    return s

SFMT_LONG = lambda x: "{0:>50s}".format(str(x))
IFMT = lambda x: "{0:>10d}".format(int(x))
FFMT = lambda x: "{0:>15.6E}".format(float(x))


def str_con(item):
    if len(item) == 0:
        return np.NaN
    return item.lower().strip()

pst_config = {}

# parameter stuff
pst_config["tied_dtype"] = np.dtype([("parnme", "a20"), ("partied","a20")])
pst_config["tied_fieldnames"] = ["parnme","partied"]
pst_config["tied_format"] = {"parnme":SFMT,"partied":SFMT}
pst_config["tied_converters"] = {"parnme":str_con,"partied":str_con}
pst_config["tied_defaults"] = {"parnme":"dum","partied":"dum"}

pst_config["par_dtype"] = np.dtype([("parnme", "a20"), ("partrans","a20"),
                                   ("parchglim","a20"),("parval1", np.float64),
                                   ("parlbnd",np.float64),("parubnd",np.float64),
                                   ("pargp","a20"),("scale", np.float64),
                                   ("offset", np.float64),("dercom",np.int)])
pst_config["par_fieldnames"] = "PARNME PARTRANS PARCHGLIM PARVAL1 PARLBND PARUBND " +\
                              "PARGP SCALE OFFSET DERCOM"
pst_config["par_fieldnames"] = pst_config["par_fieldnames"].lower().strip().split()
pst_config["par_format"] = {"parnme": SFMT, "partrans": SFMT,
                           "parchglim": SFMT, "parval1": FFMT,
                           "parlbnd": FFMT, "parubnd": FFMT,
                           "pargp": SFMT, "scale": FFMT,
                           "offset": FFMT, "dercom": IFMT}
pst_config["par_converters"] = {"parnme": str_con, "pargp": str_con}
pst_config["par_defaults"] = {"parnme":"dum","partrans":"log","parchglim":"factor",
                             "parval1":1.0,"parlbnd":1.1e-10,"parubnd":1.1e+10,
                             "pargp":"pargp","scale":1.0,"offset":0.0,"dercom":1}


# parameter group stuff
pst_config["pargp_dtype"] = np.dtype([("pargpnme", "a20"), ("inctyp","a20"),
                                   ("derinc", np.float64),
                                   ("derinclb",np.float64),("forcen","a20"),
                                   ("derincmul",np.float64),("dermthd", "a20"),
                                   ("splitthresh", np.float64),("splitreldiff",np.float64),
                                      ("splitaction","a20")])
pst_config["pargp_fieldnames"] = "PARGPNME INCTYP DERINC DERINCLB FORCEN DERINCMUL " +\
                        "DERMTHD SPLITTHRESH SPLITRELDIFF SPLITACTION"
pst_config["pargp_fieldnames"] = pst_config["pargp_fieldnames"].lower().strip().split()

pst_config["pargp_format"] = {"pargpnme":SFMT,"inctyp":SFMT,"derinc":FFMT,"forcen":SFMT,
                      "derincmul":FFMT,"dermthd":SFMT,"splitthresh":FFMT,
                      "splitreldiff":FFMT,"splitaction":SFMT}

pst_config["pargp_converters"] = {"pargpnme":str_con,"inctype":str_con,
                         "dermethd":str_con,
                         "splitaction":str_con}
pst_config["pargp_defaults"] = {"pargpnme":"pargp","inctyp":"relative","derinc":0.01,
                       "derinclb":0.0,"forcen":"switch","derincmul":2.0,
                     "dermthd":"parabolic","splitthresh":1.0e-5,
                       "splitreldiff":0.5,"splitaction":"smaller"}


# observation stuff
pst_config["obs_fieldnames"] = "OBSNME OBSVAL WEIGHT OBGNME".lower().split()
pst_config["obs_dtype"] = np.dtype([("obsnme","a20"),("obsval",np.float64),
                           ("weight",np.float64),("obgnme","a20")])
pst_config["obs_format"] = {"obsnme": SFMT, "obsval": FFMT,
                   "weight": FFMT, "obgnme": SFMT}
pst_config["obs_converters"] = {"obsnme": str_con, "obgnme": str_con}
pst_config["obs_defaults"] = {"obsnme":"dum","obsval":1.0e+10,
                     "weight":1.0,"obgnme":"obgnme"}


# prior info stuff
pst_config["null_prior"] = pd.DataFrame({"pilbl": None,
                                    "obgnme": None}, index=[])
pst_config["prior_format"] = {"pilbl": SFMT, "equation": SFMT_LONG,
                     "weight": FFMT, "obgnme": SFMT}
pst_config["prior_fieldnames"] = ["equation", "weight", "obgnme"]


# other containers
pst_config["model_command"] = []
pst_config["template_files"] = []
pst_config["input_files"] = []
pst_config["instruction_files"] = []
pst_config["output_files"] = []
pst_config["other_lines"] = []
pst_config["tied_lines"] = []
pst_config["regul_lines"] = []
pst_config["pestpp_options"] = {}


def read_resfile(resfile):
        """load a residual file into a pandas dataframe

        Parameters:
        ----------
            resfile : str
                residual file
        Returns:
        -------
            pandas DataFrame
        """
        assert os.path.exists(resfile),"read_resfile() error: resfile " +\
                                       "{0} not found".format(resfile)
        converters = {"name": str_con, "group": str_con}
        f = open(resfile, 'r')
        while True:
            line = f.readline()
            if line == '':
                raise Exception("Pst.get_residuals: EOF before finding "+
                                "header in resfile: " + resfile)
            if "name" in line.lower():
                header = line.lower().strip().split()
                break
        res_df = pd.read_csv(f, header=None, names=header, sep="\s+",
                                 converters=converters)
        res_df.index = res_df.name
        f.close()
        return res_df


def read_parfile(parfile):
    """load a pest-compatible .par file into a pandas dataframe

    Parameters:
    ----------
        parfile : str
            pest parameter file
    Returns:
    -------
        pandas DataFrame
    """
    assert os.path.exists(parfile), "Pst.parrep(): parfile not found: " +\
                                    str(parfile)
    f = open(parfile, 'r')
    header = f.readline()
    par_df = pd.read_csv(f, header=None,
                             names=["parnme", "parval1", "scale", "offset"],
                             sep="\s+")
    par_df.index = par_df.parnme
    return par_df

def write_parfile(df,parfile):
    """ write a pest parameter file from a dataframe

    Parameters:
    ----------
        df : pandas DataFrame
            with column names that correspond to the entries
            in the parameter data section of a pest control file
        parfile : str
            name of the parameter file to write
    Returns:
    -------
        None

    """
    columns = ["parnme","parval1","scale","offset"]
    formatters = {"parnme":lambda x:"{0:20s}".format(x),
                  "parval1":lambda x:"{0:20.7E}".format(x),
                  "scale":lambda x:"{0:20.7E}".format(x),
                  "offset":lambda x:"{0:20.7E}".format(x)}

    for col in columns:
        assert col in df.columns,"write_parfile() error: " +\
                                 "{0} not found in df".format(col)
    with open(parfile,'w') as f:
        f.write("single point\n")
        f.write(df.to_string(col_space=0,
                      columns=columns,
                      formatters=formatters,
                      justify="right",
                      header=False,
                      index=False,
                      index_names=False) + '\n')

def parse_tpl_file(tpl_file):
    """ parse a pest template file to get the parameter names

    Parameters:
    ----------
        tpl_file : str
            template file name
    Returns:
    -------
        list of parameter names
    """
    par_names = []
    with open(tpl_file,'r') as f:
        try:
            header = f.readline().strip().split()
            assert header[0].lower() in ["ptf","jtf"],\
                "template file error: must start with [ptf,jtf], not:" +\
                str(header[0])
            assert len(header) == 2,\
                "template file error: header line must have two entries: " +\
                str(header)

            marker = header[1]
            assert len(marker) == 1,\
                "template file error: marker must be a single character, not:" +\
                str(marker)
            for line in f:
                par_line = line.strip().split(marker)[1::2]
                for p in par_line:
                    if p not in par_names:
                        par_names.append(p)
        except Exception as e:
            raise Exception("error processing template file " +\
                            tpl_file+" :\n" + str(e))
    par_names = [pn.strip().lower() for pn in par_names]
    return par_names


def parse_ins_file(ins_file):
    """parse a pest instruction file to get observation names
    Parameters:
    ----------
        ins_file : str
            instruction file name
    Returns:
        list of observation names
    """

    obs_names = []
    with open(ins_file,'r') as f:
        header = f.readline().strip().split()
        assert header[0].lower() in ["pif","jif"],\
            "instruction file error: must start with [pif,jif], not:" +\
            str(header[0])
        marker = header[1]
        assert len(marker) == 1,\
            "instruction file error: marker must be a single character, not:" +\
            str(marker)
        for line in f:
            if marker in line:
                raw = line.strip().split(marker)
                for item in raw[::2]:
                    obs_names.extend(parse_ins_string(item))
            else:
                obs_names.extend(parse_ins_string(line.strip()))
    obs_names = [on.strip().lower() for on in obs_names]
    return obs_names


def parse_ins_string(string):
    istart_markers = ["[","(","!"]
    iend_markers = ["]",")","!"]

    obs_names = []

    idx = 0
    while True:
        if idx >= len(string) - 1:
            break
        char = string[idx]
        if char in istart_markers:
            em = iend_markers[istart_markers.index(char)]
            # print("\n",idx)
            # print(string)
            # print(string[idx+1:])
            # print(string[idx+1:].index(em))
            # print(string[idx+1:].index(em)+idx+1)
            eidx = min(len(string),string[idx+1:].index(em)+idx+1)
            obs_name = string[idx+1:eidx]
            if obs_name.lower() != "dum":
                obs_names.append(obs_name)
            idx = eidx + 1
        else:
            idx += 1
    return obs_names


def populate_dataframe(index,columns, default_dict, dtype):
    new_df = pd.DataFrame(index=index,columns=columns)
    for fieldname,dt in zip(columns,dtype.descr):
        default = default_dict[fieldname]
        new_df.loc[:,fieldname] = default
        new_df.loc[:,fieldname] = new_df.loc[:,fieldname].astype(dt[1])
    return new_df


def generic_pst(par_names=["par1"],obs_names=["obs1"]):
    """generate a generic pst instance
    Parameters:
    ----------
        par_names : list(str)
            parameter names to setup
        obs_names : list(str)
            observation names to setup
    Returns:
    -------
        Pst instance

    """
    new_pst = pyemu.Pst("pest.pst",load=False)
    pargp_data = populate_dataframe(["pargp"], new_pst.pargp_fieldnames,
                                    new_pst.pargp_defaults, new_pst.pargp_dtype)
    new_pst.parameter_groups = pargp_data

    par_data = populate_dataframe(par_names,new_pst.par_fieldnames,
                                  new_pst.par_defaults,new_pst.par_dtype)
    par_data.loc[:,"parnme"] = par_names
    par_data.index = par_names
    new_pst.parameter_data = par_data
    obs_data = populate_dataframe(obs_names,new_pst.obs_fieldnames,
                                  new_pst.obs_defaults,new_pst.obs_dtype)
    obs_data.loc[:,"obsnme"] = obs_names
    obs_data.index = obs_names
    new_pst.observation_data = obs_data

    new_pst.template_files = ["file.tpl"]
    new_pst.input_files = ["file.in"]
    new_pst.instruction_files = ["file.ins"]
    new_pst.output_files = ["file.out"]
    new_pst.model_command = ["model.bat"]

    new_pst.prior_information = new_pst.null_prior

    new_pst.other_lines = ["* singular value decomposition\n","1\n",
                           "{0:d} {1:15.6E}\n".format(new_pst.npar_adj,1.0E-6),
                           "1 1 1\n"]

    new_pst.zero_order_tikhonov()

    return new_pst


def pst_from_io_files(tpl_files,in_files,ins_files,out_files,pst_filename=None):
    """generate a Pst instance from the model io files
    Parameters:
    ----------
        tpl_files : list[str]
            list of pest template files
        in_files : list[str]
            list of corresponding model input files
        ins_files : list[str]
            list of pest instruction files
        out_files: list[str]
            list of corresponding model output files
        pst_filename : str (optional)
            name of file to write the control file to
    Returns:
    -------
        Pst instance
    """
    par_names = []
    if not isinstance(tpl_files,list):
        tpl_files = [tpl_files]
    if not isinstance(in_files,list):
        in_files = [in_files]
    assert len(in_files) == len(tpl_files),"len(in_files) != len(tpl_files)"

    for tpl_file in tpl_files:
        assert os.path.exists(tpl_file),"template file not found: "+str(tpl_file)
        par_names.extend(parse_tpl_file(tpl_file))
    
    if not isinstance(ins_files,list):
        ins_files = [ins_files]
    if not isinstance(out_files,list):
        out_files = [out_files]
    assert len(ins_files) == len(out_files),"len(out_files) != len(out_files)"


    obs_names = []
    for ins_file in ins_files:
        assert os.path.exists(ins_file),"instruction file not found: "+str(ins_file)
        obs_names.extend(parse_ins_file(ins_file))

    new_pst = generic_pst(par_names,obs_names)

    new_pst.template_files = tpl_files
    new_pst.input_files = in_files
    new_pst.instruction_files = ins_files
    new_pst.output_files = out_files

    if pst_filename:
        new_pst.write(pst_filename,update_regul=True)
    return new_pst


def get_phi_comps_from_recfile(recfile):
        """read the phi components from a record file
        Parameters:
        ----------
            recfile (str) : record file
        Returns:
        -------
            dict{iteration number:{group,contribution}}
        """
        iiter = 1
        iters = {}
        f = open(recfile,'r')
        while True:
            line = f.readline()
            if line == '':
                break
            if "starting phi for this iteration" in line.lower() or \
                "final phi" in line.lower():
                contributions = {}
                while True:
                    line = f.readline()
                    if line == '':
                        break
                    if "contribution to phi" not in line.lower():
                        iters[iiter] = contributions
                        iiter += 1
                        break
                    raw = line.strip().split()
                    val = float(raw[-1])
                    group = raw[-3].lower().replace('\"', '')
                    contributions[group] = val
        return iters

def smp_to_ins(smp_filename,ins_filename=None):
    """ create an instruction file from an smp file
    Parameters:
    ----------
        smp_filename : str
            existing smp file
        ins_filename: str:
            instruction file to create.  If None, create
            an instruction file using the smp filename
            with the ".ins" suffix
    Returns:
    -------
        dataframe instance of the smp file with the observation names and
        instruction lines as additional columns
    """
    if ins_filename is None:
        ins_filename = smp_filename+".ins"
    df = smp_to_dataframe(smp_filename)
    df.loc[:,"ins_strings"] = None
    df.loc[:,"observation_names"] = None
    name_groups = df.groupby("name").groups
    for name,idxs in name_groups.items():
        if len(name) <= 11:
            onames = df.loc[idxs,"datetime"].apply(lambda x: name+'_'+x.strftime("%d%m%Y")).values
        else:
            onames = [name+"_{0:d}".format(i) for i in range(len(idxs))]
        if False in (map(lambda x :len(x) <= 20,onames)):
            long_names = [oname for oname in onames if len(oname) > 20]
            raise Exception("observation names longer than 20 chars:\n{0}".format(str(long_names)))
        #ins_strs = ["l1  ({0:s})39:46".format(on) for on in onames]
        ins_strs = ["l1 w w w  !{0:s}!".format(on) for on in onames]


        df.loc[idxs,"observation_names"] = onames
        df.loc[idxs,"ins_strings"] = ins_strs

    with open(ins_filename,'w') as f:
        f.write("pif ~\n")
        [f.write(ins_str+"\n") for ins_str in df.loc[:,"ins_strings"]]
    return df


def dataframe_to_smp(dataframe,smp_filename,name_col="name",
                     datetime_col="datetime",value_col="value",
                     datetime_format="dd/mm/yyyy",
                     value_format="{0:15.6E}",
                     max_name_len=12):
    """ write a dataframe as an smp file

    Parameters:
    ----------
        dataframe : a pandas dataframe
        smp_filename : str
            smp file to write
        name_col: str
            the column in the dataframe the marks the site namne
        datetime_col: str
            the column in the dataframe that is a datetime instance
        value_col: str
            the column in the dataframe that is the values
        datetime_format: str
            either 'dd/mm/yyyy' or 'mm/dd/yyy'
        value_format: a python float-compatible format
    Returns:
    -------
        None
    """
    formatters = {"name":lambda x:"{0:<20s}".format(str(x)[:max_name_len]),
                  "value":lambda x:value_format.format(x)}
    if datetime_format.lower().startswith("d"):
        dt_fmt = "%d/%m/%Y    %H:%M:%S"
    elif datetime_format.lower().startswith("m"):
        dt_fmt = "%m/%d/%Y    %H:%M:%S"
    else:
        raise Exception("unrecognized datetime_format: " +\
                        "{0}".format(str(datetime_format)))

    for col in [name_col,datetime_col,value_col]:
        assert col in dataframe.columns

    dataframe.loc[:,"datetime_str"] = dataframe.loc[:,"datetime"].\
        apply(lambda x:x.strftime(dt_fmt))
    if isinstance(smp_filename,str):
        smp_filename = open(smp_filename,'w')
        # need this to remove the leading space that pandas puts in front
        s = dataframe.loc[:,[name_col,"datetime_str",value_col]].\
                to_string(col_space=0,
                          formatters=formatters,
                          justify=None,
                          header=False,
                          index=False)
        for ss in s.split('\n'):
            smp_filename.write("{0:<s}\n".format(ss.strip()))
    dataframe.pop("datetime_str")


def date_parser(items):
    """ datetime parser to help load smp files
    """
    try:
        dt = datetime.strptime(items,"%d/%m/%Y %H:%M:%S")
    except Exception as e:
        try:
            dt = datetime.strptime(items,"%m/%d/%Y %H:%M:%S")
        except Exception as ee:
            raise Exception("error parsing datetime string" +\
                            " {0}: \n{1}\n{2}".format(str(items),str(e),str(ee)))
    return dt


def smp_to_dataframe(smp_filename):
    """ load an smp file into a pandas dataframe
    Parameters:
    ----------
        smp_filename : str
            smp filename to load
    Returns:
    -------
        a pandas dataframe instance
    """
    df = pd.read_csv(smp_filename, delim_whitespace=True,
                     parse_dates={"datetime":["date","time"]},
                     header=None,names=["name","date","time","value"],
                     dtype={"name":object,"value":np.float64},
                     na_values=["dry"],
                     date_parser=date_parser)
    return df

def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)
    
def start_slaves(slave_dir,exe_rel_path,pst_rel_path,num_slaves=None,slave_root="..",
                 port=4004,rel_path=None):
    """ start a group of pest(++) slaves on the local machine

    Parameters:
    ----------
        slave_dir : (str) the path to a complete set of input files

        exe_rel_path : (str) the relative path to the pest(++)
                        executable from within the slave_dir
        pst_rel_path : (str) the relative path to the pst file
                        from within the slave_dir

        num_slaves : (int) number of slaves to start. defaults to number of cores

        slave_root : (str) the root to make the new slave directories in

        rel_path: (str) the relative path to where pest(++) should be run
                  from within the slave_dir, defaults to the uppermost level of the slave dir

    """

    assert os.path.isdir(slave_dir)
    assert os.path.isdir(slave_root)
    if num_slaves is None:
        num_slaves = mp.cpu_count()
    else:
        num_slaves = int(num_slaves)
    #assert os.path.exists(os.path.join(slave_dir,rel_path,exe_rel_path))
    exe_verf = True

    if rel_path:
        if not os.path.exists(os.path.join(slave_dir,rel_path,exe_rel_path)):
            print("warning: exe_rel_path not verified...hopefully exe is in the PATH var")
            exe_verf = False
    else:
        if not os.path.exists(os.path.join(slave_dir,exe_rel_path)):
            print("warning: exe_rel_path not verified...hopefully exe is in the PATH var")
            exe_verf = False
    if rel_path is not None:
        assert os.path.exists(os.path.join(slave_dir,rel_path,pst_rel_path))
    else:
        assert os.path.exists(os.path.join(slave_dir,pst_rel_path))
    hostname = socket.gethostname()
    port = int(port)

    tcp_arg = "{0}:{1}".format(hostname,port)

    procs = []
    base_dir = os.getcwd()
    for i in range(num_slaves):
        new_slave_dir = os.path.join(slave_root,"slave_{0}".format(i))
        if os.path.exists(new_slave_dir):
            try:
                shutil.rmtree(new_slave_dir, onerror=del_rw)
            except Exception as e:
                raise Exception("unable to remove existing slave dir:" + \
                                "{0}\n{1}".format(new_slave_dir,str(e)))
        try:
            shutil.copytree(slave_dir,new_slave_dir)
        except Exception as e:
            raise Exception("unable to copy files from slave dir: " + \
                            "{0} to new slave dir: {1}\n{2}".format(slave_dir,new_slave_dir,str(e)))
        try:
            if exe_verf:
                # if rel_path is not None:
                #     exe_path = os.path.join(rel_path,exe_rel_path)
                # else:
                exe_path = exe_rel_path
            else:
                exe_path = exe_rel_path
            args = [exe_path, pst_rel_path, "/h", tcp_arg]
            print("starting slave in {0} with args: {1}".format(new_slave_dir,args))
            if rel_path is not None:
                cwd = os.path.join(new_slave_dir,rel_path)
            else:
                cwd = new_slave_dir

            os.chdir(cwd)
            p = sp.Popen(args)
            procs.append(p)
            os.chdir(base_dir)
        except Exception as e:
            raise Exception("error starting slave: {0}".format(str(e)))

    for p in procs:
        p.wait()

def res_from_obseravtion_data(observation_data):
    res_df = observation_data.copy()
    res_df.loc[:, "name"] = res_df.pop("obsnme")
    res_df.loc[:, "measured"] = res_df.pop("obsval")
    res_df.loc[:, "group"] = res_df.pop("obgnme")
    res_df.loc[:, "modelled"] = np.NaN
    res_df.loc[:, "residual"] = np.NaN
    return res_df


