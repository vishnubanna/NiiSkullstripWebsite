import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError } from 'rxjs/operators'
import { NgxFileDropEntry, FileSystemFileEntry, FileSystemDirectoryEntry } from 'ngx-file-drop';

//error 404 to start for some reason figur out why
@Component({
  selector: 'app-fileinput',
  templateUrl: './fileinput.component.html',
  styleUrls: ['./fileinput.component.scss']
})

// alias ng = "/Users/vishnubanna/.npm-packages/bin/ng"
export class FileinputComponent implements OnInit {
  fileinput:File = null;
  //fname:string = null;
  fname:string = "Choose or Drag a Nii MRI File...";
  filename:string = null; 
  files:FileList = null;
  imgslice: any = null;
  imgsliceog: any = null;
  slice: any = "";//null; // null is not an html var so it errors, "" is the eqicvalent of null in html... just nothing 
  sliceog: any = "";//null;
  mask: any = null;
  loading : string= null;
  //disable = true;

  public dragfiles: NgxFileDropEntry[] = [];

  public dropped(files: NgxFileDropEntry[]){
    this.dragfiles = files;
      for (const dropfile of files){
        if (dropfile.fileEntry.isFile){
          const fileEntry = dropfile.fileEntry as FileSystemFileEntry; // coerse data types

          fileEntry.file((file: File) => { // temp function
            console.log(dropfile.relativePath, file);
            this.fileinput = file;
            this.fname = this.fileinput.name;
            this.fname = this.fname.replace('/', '~').replace('.', '>')
            this.filename = this.fileinput.name;
          })
        }
      }
  }


  constructor(private http: HttpClient) {

  }

  wait(ms)
  {
    var d:any = new Date();
    var d2:any = null;
    do { d2 = new Date(); }
    while(d2-d < ms);
  }


  onFileSelected(event){
    console.log(event);
    this.fileinput = event.target.files[0];
    this.fname = this.fileinput.name;
    this.fname = this.fname.replace('/', '~').replace('.', '>')
    this.filename = this.fileinput.name;
  }

  //test with a valid file
  onSubmit(){
    console.log("here");
    console.log(this.fileinput);
    if (this.fileinput === null){
      this.fname = "Choose a File Before Uploading";
      return;
    }
    this.loading = "Loading..."
    const fd = new FormData();
    fd.append("file",this.fileinput)

    this.http.post(' http://127.0.0.1:5002/api/getmask/' + this.fileinput.name, fd).subscribe(res => {
      this.imgsliceog = {filename: res['filename'], url: res['url']}
      console.log(this.imgsliceog['filename']);
      this.sliceog = this.imgsliceog['url']
      this.filename = this.imgsliceog['filename']
      console.log(this.filename);
      
      var confg:any = null;// you need a dynamic wait time... wait until url is not null or undefined
      confg = this.http.get(' http://127.0.0.1:5002/api/getmask/' + this.filename).subscribe(data => {
        this.imgslice = {url: data['url'], maskUrl: data['maskUrl']}
        console.log(this.imgslice);
        this.slice = this.imgslice['url']
        this.mask = this.imgslice['maskUrl']
        //this.disable = false;
      }, 
      error => {
        console.log(error)
        if (error.status == 400){
          this.fname = error.error.message;
          this.http.delete(' http://127.0.0.1:5002/api/getmask/' + this.filename).subscribe(
            res => {console.log(res)},
            error => {console.log(error)});
          this.filename = null;
          this.fileinput = null;
        }
      });
      return;
    }, 
    error => {
        console.log(error)
        if (error.status == 400){
          this.fname = error.error.message;
          this.http.delete(' http://127.0.0.1:5002/api/getmask/' + this.filename).subscribe(
            res => {console.log(res)},
            error => {console.log(error)});
          this.filename = null;
          this.fileinput = null;
        }
    });

    this.wait(4000);
    // var confg:any = null;// you need a dynamic wait time... wait until url is not null or undefined
    // confg = this.http.get(' http://127.0.0.1:5002/api/getmask/' + this.fileinput.name).subscribe(data => {
    //   this.imgslice = {url: data['url'], maskUrl: data['maskUrl']}
    //   console.log(this.imgslice);
    //   this.slice = this.imgslice['url']
    //   this.mask = this.imgslice['maskUrl']
    // });

    console.log(this.imgslice);
    this.loading = null;
  }
  // cors error only thrown if back end fails
  ondload(){
    // make the button grey until the file is in the database
    if (this.mask !== null){
      window.open(this.mask);
      this.mask = null;
    }
    if (this.filename === null){
      console.log("no file selected")
      return;
    }
    //this.disable = true;
    this.fname = "Choose or Drag a Nii MRI File..."
    this.fileinput = null;
    this.files = null;
    console.log(this.imgslice);
    this.wait(2000);
    // try an embedded methid 
    // while the return is null keep checking for like n times
    this.http.delete(' http://127.0.0.1:5002/api/getmask/' + this.filename).subscribe(res => {console.log(res)});
    this.filename = null;
  }

  // re render i think
  ngOnInit() {

  }

}

// export interface urls{
//     url: string;
// }
