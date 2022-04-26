version 1.0

workflow md5_n_by_m_scatter {
    input {
        Array[String] input_files
        Int scatter_input_size
    }

    call chunk_array {
         input: input_array=input_files, chunk_size=scatter_input_size
    }

    scatter (input_file_chunk in chunk_array.output_array_array) {
       call md5s { input: input_files=input_file_chunk }
   }

   output {
       Array[String] md5s_output_strings = flatten(select_all(md5s.std_output))
       # File md5s_output_file = write_lines(md5s_output_strings)
   }
}

task chunk_array {
    input {
        Array[String] input_array
        Int chunk_size
    }

    String tsv_filename = "./chunked_array.tsv"
    command <<<
        set -eux -o pipefail

        # Chunk the array into a TSV file using Python
        python3 <<CODE
        count:int = 0
        content:str = ""
        for value in ["~{sep='", "' input_array}"]:
          count += 1
          if count > 1:
              content += "\t"
          content += value
          if count >= ~{chunk_size}:
            content += "\n"
            count=0
        # Ensure the content ends with a newline
        if content[-1] != "\n":
            content += "\n"

        with open("~{tsv_filename}", "w") as fh:
            fh.write(content)
        CODE

        # Debug
        echo ~{tsv_filename}:
        cat ~{tsv_filename}
    >>>

    output {
       File chunked_array_tsv = "./chunked_array.tsv"
       Array[Array[String]] output_array_array = read_tsv(chunked_array_tsv)
    }

    runtime {
      docker: "python:3.9-bullseye"
      cpu: 1
      memory: "512 MB"
      disks: "local-disk 30 HDD"
    }
}

task md5s {
    input {
        Array[File] input_files
    }

    command <<<
        set -eux -o pipefail

        # Chunk the array into a TSV file using Python
        python3 <<CODE

        from subprocess import Popen, PIPE

        def run_subprocess(cmd, debug=False):
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()

            stdout_str = stdout.decode("utf-8").strip()
            stderr_str = stderr.decode("utf-8").strip()

            if debug:
                print("StdOut: " + stdout_str)
                print("StdErr: " + stderr_str)

            if p.returncode != 0:
                errorText = "ERROR: unable to call command: " + cmd + "\n\n" + stdout_str + "\n\n" + stderr_str
                raise Exception(errorText)

            return stdout_str


        for file in ["~{sep='", "' input_files}"]:
            output = run_subprocess(f"md5sum {file}")
            print(output)
        CODE
    >>>

     output {
        Array[String] std_output = read_lines(stdout())
     }

     runtime {
       docker: "python:3.9-bullseye"
       cpu: 1
       memory: "512 MB"
       disks: "local-disk 10 HDD"
     }
}
