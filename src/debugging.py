def debug_get_keys(fn, stopLoopIter=10_000):
    '''
    Gets all json keys from a file up to a select height (useful if the file is large like osmosis)
    You can also just look at the geneisis file to get the keys
    '''
    with open(fn, 'rb') as input_file:
        parser = ijson.parse(input_file)
        foundParents = []
        foundDataTypes = {}
        loops = 0
        for parent, data_type, value in parser:
            # print('parent={}, data_type={}, value={}'.format(parent, data_type, value))
            if parent not in foundParents:
                foundParents.append(parent)
            loops+=1

            if loops >= stopLoopIter:
                break
        print(f"{foundParents}=")
        print(f"{foundDataTypes}=")