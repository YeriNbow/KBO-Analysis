def progress_bar(count, length):
    percent = '{0:.1f}'.format(100 * (count / float(length)))
    fillin = int(round(100 * count / float(length)))
    bar = '#' * fillin + '-' * (100 - fillin)

    print(f'\r[%s] %s%s Complete' % (bar, percent, '%'), end='')
    if count == length:
        print()
