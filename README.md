# cmdprod

Cartesian product and generate command-line arguments

* Python 3.x.

* This repo is set up so that once you clone, you can do 

        pip install -e /path/to/the/folder/of/this/repo/

  to install as a Python package. In Python, we can then do `import cmdprod`,
  and all the code in `cmdprod` folder is accessible.

* `ipynb` folder is for Jupyter notebook files.

## Example

```python
import cmdprod as cp

kgroup = cp.ParamGroup(
    ['k', 'kparams'], 
    [('gauss', 1.0), ('imq', [-0.5, 1.0]), ('imq', [-0.5, 10])],
    ['--k', '--kparams']  
)
a = cp.Param('A', ['a0', 'a1'])
b = cp.Param('B', np.linspace(0, 1, 2))

# "args" represents a specification of arguments (with candidate values)
args = cp.Args([kgroup, a, b])

# An ArgsProcessor processes and formats an "args"
args_processor = cp.APPrint(prefix='script.py ', suffix=' &\n')
args_processor.iaf.value_formatter.list_value_sep = ', '
args_processor(args)
```

### Output:

    script.py --k gauss --kparams 1.0 --A a0 --B 0.0 &
    script.py --k gauss --kparams 1.0 --A a0 --B 1.0 &
    script.py --k gauss --kparams 1.0 --A a1 --B 0.0 &
    script.py --k gauss --kparams 1.0 --A a1 --B 1.0 &
    script.py --k imq --kparams -0.5, 1.0 --A a0 --B 0.0 &
    script.py --k imq --kparams -0.5, 1.0 --A a0 --B 1.0 &
    script.py --k imq --kparams -0.5, 1.0 --A a1 --B 0.0 &
    script.py --k imq --kparams -0.5, 1.0 --A a1 --B 1.0 &
    script.py --k imq --kparams -0.5, 10 --A a0 --B 0.0 &
    script.py --k imq --kparams -0.5, 10 --A a0 --B 1.0 &
    script.py --k imq --kparams -0.5, 10 --A a1 --B 0.0 &
    script.py --k imq --kparams -0.5, 10 --A a1 --B 1.0 &
    
