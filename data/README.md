# Kaiju OTU table

    wget https://kaiju.binf.ku.dk/database/kaiju_db_nr_euk_2021-02-24.tgz
    tar -xf kaiju_db_nr_euk_2021-02-24.tgz

For every sample in the collection downloaded:

    kaiju -t nodes.dmp -f kaiju_db_nr_euk.fmi -i reads.fastq [-j reads2.fastq]
    kaiju2table -t nodes.dmp -n names.dmp -r genus -o kaiju.table input1.tsv [input2.tsv ...]
    
