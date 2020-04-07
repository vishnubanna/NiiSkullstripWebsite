import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { FileinputComponent } from './fileinput.component';

describe('FileinputComponent', () => {
  let component: FileinputComponent;
  let fixture: ComponentFixture<FileinputComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ FileinputComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(FileinputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
