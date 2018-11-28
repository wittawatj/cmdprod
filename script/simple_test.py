import cmdperm as cp

def main():
    pk = cp.Param('k', ['gauss', 'imq'])
    pkparams = cp.Param('kparams', [1, 2, 3.2])

    formatter = cp.IAFArgparse(pv_sep=' ')
    args = cp.Args([pk, pkparams])
    for ar in args:
        print(formatter(ar))

if __name__ == '__main__':
    main()
