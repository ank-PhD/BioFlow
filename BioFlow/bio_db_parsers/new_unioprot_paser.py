"""
The module responsible for parsing of the Uniprot SWISSPROT .dat file for a subset of
cross-references that are useful in our database.

Once uniprot is parsed, it is returned as the dictionary containing the following elements:

Uniprot = { SWISSPROT_ID:{
    'Acnum':[],
    'Names': {'Full': '', 'AltNames': []},
    'GeneRefs': {'Names': [], 'OrderedLocusNames': [], 'ORFNames': []},
    'TaxID': '',
    'Ensembl': [],
    'KEGG': [],
    'EMBL': [],
    'GO': [],
    'Pfam': [],
    'SUPFAM': [],
    'PDB': [],
    'GeneID': [], }}
"""
import copy
import BioFlow.main_configs as conf
from BioFlow.utils.log_behavior import logger
from BioFlow.internals_config import interesting_lines, interesting_xrefs,\
    names_to_ignore, starting_dict


class UniProtParser(object):

    def __init__(self, tax_ids_to_parse):
        """

        :param tax_ids_to_parse: list of NCBI taxonomy identifiers we are interested in
        :return:
        """
        self._ignore = [False, 2]  # TODO: second element of Ignore does not get used. Is it normal?
        self.dico = {}
        self.uniprot = {}
        self.parsed = False
        self.tax_id_list = tax_ids_to_parse

    def parse_xref(self, line):
        """
        Parses an xref line from the Uniprot text file and updates the provided dictionary with the
        results of parsing

        :param line:
        """
        print 'debug: x-ref', line
        if 'EMBL; ' in line and 'ChEMBL' not in line:
            contents_list = line.split(';')
            if len(contents_list) > 4:
                package = {'Accession': contents_list[1].strip(),
                           'ID': contents_list[2].strip(),
                           'status': contents_list[3].strip(),
                           'type': contents_list[4].strip().strip('.')}
            else:
                package = {'Accession': contents_list[1].strip(),
                           'ID': contents_list[2].strip(),
                           'status': contents_list[3].strip(),
                           'type': ''}

            self.dico['EMBL'].append(package)
        if 'GO; GO:' in line:
            self.dico['GO'].append(line.split(';')[1].split(':')[1].strip())
        if 'Pfam; ' in line:
            self.dico['Pfam'].append(line.split(';')[1].strip())
        if 'SUPFAM; ' in line:
            self.dico['SUPFAM'].append(line.split(';')[1].strip())
        if 'Ensembl; ' in line:
            self.dico['Ensembl'].append(line.split(';')[1].strip())
            self.dico['Ensembl'].append(line.split(';')[2].strip())
            self.dico['Ensembl'].append(line.split(';')[3].strip().strip('.'))
        if 'KEGG; ' in line:
            self.dico['KEGG'].append(line.split(';')[1].strip())
        if 'PDB; ' in line:
            self.dico['PDB'].append(line.split(';')[1].strip())
        if 'GeneID; ' in line:
            self.dico['GeneID'].append(line.split(';')[1].strip())

    def parse_gene_references(self, line):
        """
        Parses gene names and references from the UNIPROT text file

        :param line:
        """
        words = filter(lambda x: x != '', str(line[2:].strip() + ' ').split('; '))
        for word in words:
            if 'ORFNames' in word:
                for subword in word.split('=')[1].strip().split(','):
                    self.dico['GeneRefs']['ORFNames'].append(subword.strip())
            if 'OrderedLocusNames' in word:
                for subword in word.split('=')[1].strip().split(','):
                    self.dico['GeneRefs']['OrderedLocusNames'].append(subword.strip())
            if 'Name=' in word or 'Synonyms=' in word:
                for subword in word.split('=')[1].strip().split(','):
                    self.dico['GeneRefs']['Names'].append(subword.strip())

    def parse_name(self, line):
        """
        Parses a line that contains a name associated to the entry we are trying to load

        :param line:
        :return:
        """
        if 'RecName: Full=' in line:
            self.dico['Names']['Full'] = line.split('RecName: Full=')[1].split(';')[0]
            return ''
        if 'AltName: Full=' in line:
            self.dico['Names']['AltNames'].append(
                line.split('AltName: Full=')[1].split(';')[0])
            return ''
        if 'Short=' in line:
            self.dico['Names']['AltNames'].append(line.split('Short=')[1].split(';')[0])
            return ''
        if self._ignore[0]:
            if self._ignore[1] == 0:
                self._ignore[0] = False
                self._ignore[1] = 2
                return ''
            else:
                return ''
        if ' Includes:' in line:
            self._ignore[0] = True
            return ''
        if any(x in line for x in names_to_ignore):
            return ''

    def process_line(self, line, keyword):
        """
        A function that processes a line parsed from the UNIPROT database file

        :param line:
        :param keyword:
        """
        print 'debug-main'
        if keyword == 'ID':
            words = filter(lambda a: a != '', line.split(' '))
            self.dico['ID'] = words[1]
        if keyword == 'AC':
            words = filter(lambda a: a != '', line.split(' '))
            for word in words[1:]:
                self.dico['Acnum'].append(word.split(';')[0])
        if keyword == 'OX':
            self.dico['TaxID'] = line.split('NCBI_TaxID=')[1].split(';')[0]
        if keyword == 'DE':
            self.parse_name(line)
        if keyword == 'GN':
            self.parse_gene_references(line)
        if keyword == 'DR' and any(x in line for x in interesting_xrefs):
            self.parse_xref(line)

    def end_block(self):
        """
        Manages the behavior of the end of a parse block

        :return:
        """
        if self.dico['TaxID'] in self.tax_id_list:
            self._ignore[0] = False
            self.uniprot[self.dico['ID']] = self.dico
        return copy.deepcopy(starting_dict)

    def parse_uniprot(self, source_path=conf.UNIPROT_source):
        """
        Performs the entire uniprot file parsing and importing

        :param source_path: path towards the uniprot test file
        :return: uniprot parse dictionary
        """
        self.dico = copy.deepcopy(starting_dict)
        source_file = open(source_path, "r")
        line_counter = 0
        while True:
            line = source_file.readline()
            line_counter += 1
            if not line:
                break
            keyword = line[0:2]
            if keyword == '//':
                self.dico = self.end_block()
            if keyword in interesting_lines:
                self.process_line(line, keyword)

        logger.info("%s lines scanned during UNIPROT import" % line_counter)
        self.parsed = True
        return self.uniprot

    def get_access_dicts(self):
        """
        Returns an access dictionary that would plot genes names, AcNums or EMBL identifiers to the
        Swissprot IDs

        :return: dictionary mapping all teh external database identifiers towards uniprot IDs
        """
        if not self.parsed:
            logger.warning('Attempting to get access points to a non-parsed uniprot object')
        access_dict = {}
        for key in self.uniprot.keys():
            for sub_element in self.uniprot[key]['KEGG']:
                access_dict[sub_element] = key
            for sub_element in self.uniprot[key]['Ensembl']:
                access_dict[sub_element] = key
            for sub_element in self.uniprot[key]['EMBL']:
                access_dict[sub_element['Accession']] = key
                access_dict[sub_element['ID']] = key
            for sub_element in self.uniprot[key]['Acnum']:
                access_dict[sub_element] = key
            for sub_element in self.uniprot[key]['GeneRefs']['Names']:
                access_dict[sub_element] = key
            for sub_element in self.uniprot[key]['GeneRefs']['OrderedLocusNames']:
                access_dict[sub_element] = key
            for sub_element in self.uniprot[key]['GeneRefs']['ORFNames']:
                access_dict[sub_element] = key
        return access_dict