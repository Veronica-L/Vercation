def get_few_shot(df_str, cve_info):
    cve_list = [
    {
        'idx': 1,
        'text': '''
I will provide you with a CWE ID, CWE ID, CVE description, and patch code. Please extract the vulnerability logic from the patch context and indicate which lines are relevant to the vulnerability logic.     
Provide response only in following format: 
'vulnerability logic: <text>'
'vulnerable lines : [<Line number List>] ' 
Do not include the added lines number (with +) and anything else in response.

CVE ID: CVE-2023-1579
CWE ID: CWE-119 Improper Restriction of Operations within the Bounds of a Memory Buffer
CWE-787 Out-of-bounds Write
CVE Description: Heap based buffer overflow in binutils-gdb/bfd/libbfd.c in bfd_getl64.
patch code:
493  static int mxf_read_primer_pack(void *arg, AVIOContext *pb, int tag, int size, UID uid, int64_t klv_offset)
494  {
495      MXFContext *mxf = arg;
496      int item_num = avio_rb32(pb);
497      int item_len = avio_rb32(pb);
498      if (item_len != 18) {
499          avpriv_request_sample(pb, "Primer pack item length %d", item_len);
501          return AVERROR_PATCHWELCOME;
502      }
503  -   if (item_num > 65536) {
503  +   if (item_num > 65536 || item_num < 0) {
504          av_log(mxf->fc, AV_LOG_ERROR, "item_num %d is too large\n", item_num);
505          return AVERROR_INVALIDDATA;
506      }
507      if (mxf->local_tags)
508          av_log(mxf->fc, AV_LOG_VERBOSE, "Multiple primer packs\n");
509      av_free(mxf->local_tags);
510      mxf->local_tags_count = 0;
511      mxf->local_tags = av_calloc(item_num, item_len);
512      if (!mxf->local_tags)
513          return AVERROR(ENOMEM);
514      mxf->local_tags_count = item_num;
515      avio_read(pb, mxf->local_tags, item_num*item_len);
516      return 0;
517  }''',
        'in_training': True,
        'logic': '''
vulnerability logic:
1. If the value of item_num is greater than 65536, the original code does not consider the possibility that item_num may be a negative value, thus bypassing this check.
2. Subsequently, the value of item_num is used to allocate memory space for mxf->local_tags. If item_num is an illegal negative value, it may result in allocating a memory area that is too small.
3. Finally, the data is read into the allocated mxf->local_tags area using avio_read. If the space is insufficient, a buffer overflow may occur.''',
        'lines': '''
vulnerable lines: [503, 511, 515]'''
    },
    {
        'idx': 2,
        'text': '''
I will provide you with a CWE ID, CWE ID, CVE description, and patch code. Please extract the vulnerability logic from the patch context and indicate which lines are relevant to the vulnerability logic. 
Provide response only in following format: 
'vulnerability logic: <text>'
'vulnerable lines : [<Line number List>] ' 
Do not include the added lines number (with +) and anything else in response.

 CVE ID: CVE-2019-17451
CWE ID: CWE-190 Integer Overflow or Wraparound
CVE Description: An issue was discovered in the Binary File Descriptor (BFD) library (aka libbfd), as distributed in GNU Binutils 2.32. It is an integer overflow leading to a SEGV in _bfd_dwarf2_find_nearest_line in dwarf2.c, as demonstrated by nm.
patch code: 
4439	    for (total_size = 0;
4440	  	   msec;
4441	  	   msec = find_debug_info (debug_bfd, debug_sections, msec))
4442	- 	total_size += msec->size;
4442	+ 	{
4443	+ 	  /* Catch PR25070 testcase overflowing size calculation here.  */
4444	+ 	  if (total_size + msec->size < total_size
4445	+ 	      || total_size + msec->size < msec->size)
4446	+ 	    {
4447	+ 	      bfd_set_error (bfd_error_no_memory);
4448	+ 	      return FALSE;
4449	+ 	    }
4450	+ 	  total_size += msec->size;
4451	+ 	}
4443	  
4444	        stash->info_ptr_memory = (bfd_byte *) bfd_malloc (total_size);
4445	        if (stash->info_ptr_memory == NULL)
4446	  	return FALSE;
4447	  
4448	        total_size = 0;
4449	        for (msec = find_debug_info (debug_bfd, debug_sections, NULL);
4450	  	   msec;
4451	  	   msec = find_debug_info (debug_bfd, debug_sections, msec))
4452	  	{
4453	  	  bfd_size_type size;
4454	  
4455	  	  size = msec->size;
4456	  	  if (size == 0)
4457	  	    continue;
4458	  
4459	  	  if (!(bfd_simple_get_relocated_section_contents
4460	  		(debug_bfd, msec, stash->info_ptr_memory + total_size,
4461	  		 symbols)))
4462	  	    return FALSE;
4463	  
4464	  	  total_size += size;
4465	  	}
4466	      }
4467	  
4468	    stash->info_ptr = stash->info_ptr_memory;
4469	    stash->info_ptr_end = stash->info_ptr + total_size;
4470	    stash->sec = find_debug_info (debug_bfd, debug_sections, NULL);
4471	    stash->sec_info_ptr = stash->info_ptr;
4472	    return TRUE;''',
        'in_training': True,
        'logic': '''
vulnerability logic:
1. In the original code, when accumulating the sizes of various sections (msec->size), there is no check for potential integer overflow.
2. If total_size overflows to a smaller value, it may lead to insufficient memory allocation.
3. When accessing this memory block using stash->info_ptr_memory, there may be an out-of-bounds access, potentially resulting in a segmentation fault.''',
        'lines': '''
vulnerable lines: [4442, 4444, 4459, 4460, 4461]'''
    },
    {
        'idx': 3,
        'text': f'''
I will provide you with a CWE ID, CWE ID, CVE description, and patch code. Please extract the vulnerability logic from the patch context and indicate which lines are relevant to the vulnerability logic. 
Provide response only in following format: 
'vulnerability logic: <text>'
'vulnerable lines : [<Line number List>] ' 
Do not include the added lines number (with +) and anything else in response.

CVE ID: {cve_info['cve_number']}
CWE ID: {cve_info['cwe']}
CVE Description: {cve_info['description']}
patch code: {df_str}
''',
        'in_training': False,
    }
]
    return cve_list